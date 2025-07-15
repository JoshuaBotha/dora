"""
Directory Explorer Package - FastAPI Version
A FastAPI web application for exploring directory sizes with interactive pie charts
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for API responses
class DirectoryItem(BaseModel):
    name: str
    size: int
    type: str  # "file" or "directory"
    path: str

class DirectoryAnalysis(BaseModel):
    path: str
    total_size: int
    items: List[DirectoryItem]
    parent: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

class SizeFormatResponse(BaseModel):
    size: int
    formatted: str

class SetRootRequest(BaseModel):
    path: str

class SetRootResponse(BaseModel):
    success: bool
    message: str
    new_root: str

class DirectoryAnalyzer:
    """Analyzes directory structure and calculates sizes with async support"""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path).resolve()
        self.cache: Dict[str, int] = {}
        self.executor = ThreadPoolExecutor(max_workers=4)

    def set_root_path(self, new_root: str) -> bool:
        """Set a new root path and clear cache"""
        try:
            new_path = Path(new_root).resolve()
            if not new_path.exists() or not new_path.is_dir():
                return False

            self.root_path = new_path
            self.cache.clear()  # Clear cache when root changes
            logger.info(f"Root path changed to: {self.root_path}")
            return True
        except Exception as e:
            logger.error(f"Error setting root path: {e}")
            return False

    def _get_directory_size_sync(self, path: Path) -> int:
        """Synchronous directory size calculation for thread pool"""
        if str(path) in self.cache:
            return self.cache[str(path)]

        total_size = 0
        try:
            for item in path.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
        except (OSError, PermissionError):
            logger.warning(f"Permission denied for {path}")
            return 0

        self.cache[str(path)] = total_size
        return total_size

    async def get_directory_size(self, path: Path) -> int:
        """Async directory size calculation"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._get_directory_size_sync, path
        )

    async def analyze_directory(self, path: str) -> DirectoryAnalysis:
        """Analyze directory and return size data for visualization"""
        path_obj = Path(path)
        if not path_obj.exists() or not path_obj.is_dir():
            raise HTTPException(
                status_code=404,
                detail="Directory not found or not accessible"
            )

        items = []
        total_size = 0

        try:
            # Process items concurrently
            tasks = []
            item_paths = []

            for item in path_obj.iterdir():
                if item.name.startswith('.'):
                    continue  # Skip hidden files/directories

                item_paths.append(item)
                if item.is_dir():
                    tasks.append(self.get_directory_size(item))
                else:
                    tasks.append(asyncio.create_task(self._get_file_size(item)))

            if tasks:
                sizes = await asyncio.gather(*tasks, return_exceptions=True)

                for item, size in zip(item_paths, sizes):
                    if isinstance(size, Exception):
                        logger.warning(f"Cannot access {item}: {size}")
                        continue

                    item_type = "directory" if item.is_dir() else "file"
                    items.append(DirectoryItem(
                        name=item.name,
                        size=size,
                        type=item_type,
                        path=str(item)
                    ))
                    total_size += size

        except (OSError, PermissionError) as e:
            raise HTTPException(status_code=403, detail="Permission denied")

        # Sort by size (descending)
        items.sort(key=lambda x: x.size, reverse=True)

        parent_path = None
        if path_obj != self.root_path:
            parent_path = str(path_obj.parent)

        return DirectoryAnalysis(
            path=str(path_obj),
            total_size=total_size,
            items=items,
            parent=parent_path
        )

    async def _get_file_size(self, file_path: Path) -> int:
        """Get file size asynchronously"""
        try:
            return file_path.stat().st_size
        except (OSError, PermissionError):
            return 0

def create_app(root_directory: Optional[str] = None) -> FastAPI:
    """Create FastAPI application"""

    if root_directory is None:
        root_directory = os.getcwd()

    # Validate root directory
    root_path = Path(root_directory).resolve()
    if not root_path.exists() or not root_path.is_dir():
        raise ValueError(f"Invalid root directory: {root_directory}")

    analyzer = DirectoryAnalyzer(str(root_path))

    # Create FastAPI app with metadata
    app = FastAPI(
        title="Directory Explorer",
        description="Explore directory sizes with interactive pie charts",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Mount static files if they exist
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    @app.get("/", response_class=HTMLResponse, tags=["Frontend"])
    async def get_index():
        """Serve the main web interface"""
        return HTMLResponse(content=HTML_TEMPLATE)

    @app.get("/api/analyze", response_model=DirectoryAnalysis, tags=["Analysis"])
    async def analyze_directory(
            path: Optional[str] = Query(None, description="Directory path to analyze")
    ):
        """
        Analyze directory and return size data for visualization
        
        - **path**: Directory path to analyze (defaults to root directory)
        """
        if path is None:
            path = str(analyzer.root_path)

        # Security check: ensure path is within root directory
        try:
            requested_path = Path(path).resolve()
            if not str(requested_path).startswith(str(analyzer.root_path)):
                raise HTTPException(
                    status_code=403,
                    detail="Access denied - path outside root directory"
                )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

        return await analyzer.analyze_directory(path)

    @app.post("/api/set-root", response_model=SetRootResponse, tags=["Navigation"])
    async def set_root_directory(request: SetRootRequest):
        """
        Set a new root directory for exploration
        
        - **path**: New root directory path
        """
        try:
            new_path = Path(request.path).resolve()

            # Validate the path exists and is a directory
            if not new_path.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Directory does not exist: {request.path}"
                )

            if not new_path.is_dir():
                raise HTTPException(
                    status_code=400,
                    detail=f"Path is not a directory: {request.path}"
                )

            # Check if we have read access
            try:
                list(new_path.iterdir())
            except PermissionError:
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied for directory: {request.path}"
                )

            # Set the new root
            success = analyzer.set_root_path(str(new_path))

            if success:
                return SetRootResponse(
                    success=True,
                    message="Root directory updated successfully",
                    new_root=str(analyzer.root_path)
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to set new root directory"
                )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid path: {str(e)}"
            )

    @app.get("/api/current-root", tags=["Navigation"])
    async def get_current_root():
        """Get the current root directory"""
        return {"current_root": str(analyzer.root_path)}

    @app.get("/api/format_size/{size}", response_model=SizeFormatResponse, tags=["Utilities"])
    async def format_size_endpoint(size: int):
        """Format byte size to human readable format"""
        formatted = format_bytes(size)
        return SizeFormatResponse(size=size, formatted=formatted)

    @app.get("/api/health", tags=["Health"])
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "root_directory": str(analyzer.root_path)}

    return app

def format_bytes(bytes_size: int) -> str:
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"

# Enhanced HTML Template with better error handling
with open(Path(__file__).parent / "index.html", "r") as f:
    HTML_TEMPLATE = f.read()

def main():
    """Main entry point"""
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description='Directory Explorer FastAPI App')
    parser.add_argument('--directory', '-d', default=os.getcwd(),
                        help='Root directory to explore (default: current directory)')
    parser.add_argument('--port', '-p', type=int, default=8000,
                        help='Port to run the web server on (default: 8000)')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Host to bind the web server to (default: 127.0.0.1)')
    parser.add_argument('--reload', action='store_true',
                        help='Enable auto-reload for development')
    parser.add_argument('--workers', type=int, default=1,
                        help='Number of worker processes')

    args = parser.parse_args()

    # Validate directory
    if not Path(args.directory).exists():
        print(f"❌ Error: Directory '{args.directory}' does not exist")
        return 1

    if not Path(args.directory).is_dir():
        print(f"❌ Error: '{args.directory}' is not a directory")
        return 1

    print(f"🚀 Starting Directory Explorer (FastAPI)")
    print(f"📁 Root directory: {Path(args.directory).resolve()}")
    print(f"🌐 Web interface: http://{args.host}:{args.port}")
    print(f"📚 API documentation: http://{args.host}:{args.port}/docs")
    print(f"🔍 Click on pie chart slices to navigate into directories")
    print(f"⌨️  Keyboard shortcuts: ESC (back), F5/Ctrl+R (refresh)")

    # Create app with specified directory
    app = create_app(args.directory)

    # Run with uvicorn
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        access_log=True
    )

if __name__ == '__main__':
    main()