# Dora the Directory Explorer

A modern FastAPI web application for exploring directory sizes with interactive pie charts. Click on pie chart slices to navigate into subdirectories and visualize disk usage patterns with async performance.

## Features

- **🚀 FastAPI Backend**: Modern async Python web framework with automatic API documentation
- **📊 Interactive Pie Charts**: Visualize directory contents with clickable pie chart slices
- **🔍 Directory Navigation**: Click on directory slices to drill down into subdirectories
- **⚡ Async Performance**: Concurrent directory size calculations for better performance
- **🔒 Security**: Restricts access to files within the specified root directory
- **💾 Caching**: Intelligent caching of directory size calculations
- **📱 Responsive Design**: Clean, modern web interface with Chart.js visualizations
- **📚 Auto Documentation**: Built-in API documentation at `/docs` and `/redoc`
- **🎯 Type Safety**: Full type hints with Pydantic models

## Installation

```bash
pip install directory-explorer
```

Or install from source:

```bash
git clone https://github.com/yourusername/directory-explorer.git
cd directory-explorer
pip install -e .
```

## Usage

### Command Line

```bash
# Explore current directory
directory-explorer

# Explore specific directory
directory-explorer -d /path/to/directory

# Run on different port (default: 8000)
directory-explorer -p 9000

# Run with auto-reload for development
directory-explorer --reload

# Run on all interfaces
directory-explorer --host 0.0.0.0

# Run with multiple workers
directory-explorer --workers 4
```

### Python API

```python
from directory_explorer import create_app
import uvicorn

# Create FastAPI app
app = create_app('/path/to/root/directory')

# Run with uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8000
CMD ["directory-explorer", "--host", "0.0.0.0", "--port", "8000"]
```

## Project Structure

```
directory-explorer/
├── directory_explorer/
│   ├── __init__.py
│   ├── main.py              # Main FastAPI application
│   └── static/              # Static files (if any)
├── setup.py
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── Dockerfile
└── tests/
    └── test_directory_explorer.py
```

## API Endpoints

### Web Interface
- `GET /` - Main web interface with interactive charts

### API Endpoints
- `GET /api/analyze?path=<path>` - Analyze directory and return structured JSON data
- `GET /api/format_size/{size}` - Format byte size to human readable format
- `GET /api/health` - Health check endpoint

### Documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)
- `GET /openapi.json` - OpenAPI schema

## API Response Models

### Directory Analysis Response
```json
{
  "path": "/path/to/directory",
  "total_size": 1048576,
  "items": [
    {
      "name": "subdirectory",
      "size": 524288,
      "type": "directory",
      "path": "/path/to/directory/subdirectory"
    }
  ],
  "parent": "/path/to"
}
```

## Security Features

- **Path Traversal Protection**: Prevents access outside the specified root directory
- **Input Validation**: Pydantic models ensure type safety and data validation
- **Error Handling**: Graceful handling of permission errors and invalid paths
- **Hidden File Exclusion**: Hidden files and directories (starting with `.`) are excluded by default

## Performance

- **Async Processing**: Concurrent directory size calculations using asyncio
- **Thread Pool**: CPU-intensive operations run in thread pool executors
- **Intelligent Caching**: Directory size calculations are cached to avoid redundant work
- **Efficient File I/O**: Optimized file system operations

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests with coverage
pytest --cov=directory_explorer

# Run async tests
pytest -m asyncio

# Format code
black directory_explorer/

# Type checking
mypy directory_explorer/

# Lint code
flake8 directory_explorer/

# Run development server with auto-reload
directory-explorer --reload
```

## Environment Variables

```bash
# Optional environment variables
DIRECTORY_EXPLORER_ROOT=/path/to/root    # Default root directory
DIRECTORY_EXPLORER_HOST=0.0.0.0          # Default host
DIRECTORY_EXPLORER_PORT=8000             # Default port
DIRECTORY_EXPLORER_WORKERS=1             # Number of workers
```

## Monitoring and Observability

The FastAPI application includes built-in support for:
- Health checks at `/api/health`
- Request/response logging
- Prometheus metrics (with additional setup)
- Structured error responses

## License

MIT License - see LICENSE file for details.
