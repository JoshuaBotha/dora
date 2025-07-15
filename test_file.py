# tests/test_directory_explorer.py
import pytest
import tempfile
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
import httpx

from directory_explorer.main import DirectoryAnalyzer, create_app, format_bytes


class TestDirectoryAnalyzer:
    def setup_method(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.analyzer = DirectoryAnalyzer(self.test_dir)
        
        # Create test structure
        test_structure = {
            'file1.txt': 100,
            'file2.txt': 200,
            'subdir1': {
                'subfile1.txt': 300,
                'subfile2.txt': 400,
            },
            'subdir2': {
                'subfile3.txt': 500,
            }
        }
        
        self._create_test_structure(Path(self.test_dir), test_structure)
    
    def _create_test_structure(self, base_path, structure):
        """Create test files and directories"""
        for name, content in structure.items():
            path = base_path / name
            if isinstance(content, dict):
                path.mkdir()
                self._create_test_structure(path, content)
            else:
                path.write_text('x' * content)
    
    @pytest.mark.asyncio
    async def test_get_directory_size(self):
        """Test directory size calculation"""
        # Test root directory size
        total_size = await self.analyzer.get_directory_size(Path(self.test_dir))
        expected_size = 100 + 200 + 300 + 400 + 500  # Sum of all file sizes
        assert total_size == expected_size
        
        # Test subdirectory size
        subdir1_path = Path(self.test_dir) / 'subdir1'
        subdir1_size = await self.analyzer.get_directory_size(subdir1_path)
        assert subdir1_size == 700  # 300 + 400
    
    @pytest.mark.asyncio
    async def test_analyze_directory(self):
        """Test directory analysis"""
        result = await self.analyzer.analyze_directory(self.test_dir)
        
        assert result.path == self.test_dir
        assert result.total_size == 1500
        assert len(result.items) == 4  # 2 files + 2 subdirs
        
        # Check that items are sorted by size (descending)
        sizes = [item.size for item in result.items]
        assert sizes == sorted(sizes, reverse=True)
        
        # Check item types
        items_by_name = {item.name: item for item in result.items}
        assert items_by_name['file1.txt'].type == 'file'
        assert items_by_name['subdir1'].type == 'directory'
    
    @pytest.mark.asyncio
    async def test_nonexistent_directory(self):
        """Test handling of nonexistent directory"""
        with pytest.raises(Exception):  # Should raise HTTPException
            await self.analyzer.analyze_directory('/nonexistent/path')


class TestFormatBytes:
    def test_format_bytes(self):
        """Test byte formatting"""
        assert format_bytes(0) == "0.0 B"
        assert format_bytes(1023) == "1023.0 B"
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"


class TestFastAPIApp:
    def setup_method(self):
        """Set up test FastAPI app"""
        self.test_dir = tempfile.mkdtemp()
        self.app = create_app(self.test_dir)
        self.client = TestClient(self.app)
        
        # Create test file
        test_file = Path(self.test_dir) / 'test.txt'
        test_file.write_text('test content')
    
    def test_index_route(self):
        """Test main page route"""
        response = self.client.get('/')
        assert response.status_code == 200
        assert 'Directory Explorer' in response.text
    
    def test_analyze_api(self):
        """Test analyze API endpoint"""
        response = self.client.get('/api/analyze')
        assert response.status_code == 200
        
        data = response.json()
        assert 'path' in data
        assert 'total_size' in data
        assert 'items' in data
        assert len(data['items']) == 1  # Just the test file
    
    def test_analyze_api_with_path(self):
        """Test analyze API with specific path"""
        response = self.client.get(f'/api/analyze?path={self.test_dir}')
        assert response.status_code == 200
        
        data = response.json()
        assert data['path'] == self.test_dir
    
    def test_analyze_api_security(self):
        """Test that API prevents path traversal"""
        # Try to access parent directory
        parent_dir = str(Path(self.test_dir).parent)
        response = self.client.get(f'/api/analyze?path={parent_dir}')
        assert response.status_code == 403
        
        data = response.json()
        assert 'detail' in data
        assert 'Access denied' in data['detail']
    
    def test_format_size_api(self):
        """Test format size API endpoint"""
        response = self.client.get('/api/format_size/1024')
        assert response.status_code == 200
        
        data = response.json()
        assert data['formatted'] == '1.0 KB'
        assert data['size'] == 1024
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/api/health')
        assert response.status_code == 200
        
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'root_directory' in data
    
    def test_api_documentation(self):
        """Test that API documentation is available"""
        response = self.client.get('/docs')
        assert response.status_code == 200
        
        response = self.client.get('/redoc')
        assert response.status_code == 200
    
    def test_openapi_schema(self):
        """Test OpenAPI schema generation"""
        response = self.client.get('/openapi.json')
        assert response.status_code == 200
        
        schema = response.json()
        assert 'openapi' in schema
        assert 'info' in schema
        assert schema['info']['title'] == 'Directory Explorer'


class TestAsyncPerformance:
    def setup_method(self):
        """Set up performance test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.analyzer = DirectoryAnalyzer(self.test_dir)
        
        # Create larger test structure for performance testing
        self._create_large_structure()
    
    def _create_large_structure(self):
        """Create a larger directory structure for performance testing"""
        base_path = Path(self.test_dir)
        
        # Create multiple subdirectories with files
        for i in range(10):
            subdir = base_path / f'subdir_{i}'
            subdir.mkdir()
            
            for j in range(20):
                file_path = subdir / f'file_{j}.txt'
                file_path.write_text('x' * (100 * (j + 1)))  # Variable file sizes
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis(self):
        """Test concurrent directory analysis"""
        # Analyze multiple subdirectories concurrently
        subdirs = [self.test_dir / f'subdir_{i}' for i in range(5)]
        
        tasks = [
            self.analyzer.analyze_directory(str(subdir)) 
            for subdir in subdirs if subdir.exists()
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all analyses completed successfully
        assert len(results) == len(tasks)
        for result in results:
            assert result.total_size > 0
            assert len(result.items) > 0


class TestErrorHandling:
    def setup_method(self):
        """Set up error handling tests"""
        self.test_dir = tempfile.mkdtemp()
        self.app = create_app(self.test_dir)
        self.client = TestClient(self.app)
    
    def test_invalid_path_parameter(self):
        """Test handling of invalid path parameters"""
        response = self.client.get('/api/analyze?path=')
        # Empty path should default to root directory
        assert response.status_code == 200
        
        response = self.client.get('/api/analyze?path=null')
        # Invalid path should return error
        assert response.status_code in [400, 403, 404]
    
    def test_malformed_requests(self):
        """Test handling of malformed requests"""
        # Test invalid size parameter
        response = self.client.get('/api/format_size/invalid')
        assert response.status_code == 422  # Validation error
        
        # Test negative size
        response = self.client.get('/api/format_size/-100')
        assert response.status_code == 422  # Validation error


class TestIntegration:
    """Integration tests that test the full workflow"""
    
    def setup_method(self):
        """Set up integration test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.app = create_app(self.test_dir)
        self.client = TestClient(self.app)
        
        # Create realistic directory structure
        self._create_realistic_structure()
    
    def _create_realistic_structure(self):
        """Create a realistic directory structure"""
        base = Path(self.test_dir)
        
        # Create a project-like structure
        (base / 'src').mkdir()
        (base / 'src' / 'main.py').write_text('print("hello")' * 100)
        (base / 'src' / 'utils.py').write_text('def helper(): pass' * 50)
        
        (base / 'tests').mkdir()
        (base / 'tests' / 'test_main.py').write_text('def test_main(): pass' * 30)
        
        (base / 'docs').mkdir()
        (base / 'docs' / 'readme.md').write_text('# Documentation\n' * 200)
        
        (base / 'requirements.txt').write_text('fastapi\nuvicorn\npydantic')
    
    def test_full_navigation_workflow(self):
        """Test complete navigation workflow"""
        # Start at root
        response = self.client.get('/api/analyze')
        assert response.status_code == 200
        root_data = response.json()
        
        # Find a directory to navigate into
        directories = [item for item in root_data['items'] if item['type'] == 'directory']
        assert len(directories) > 0
        
        # Navigate into first directory
        first_dir = directories[0]
        response = self.client.get(f'/api/analyze?path={first_dir["path"]}')
        assert response.status_code == 200
        subdir_data = response.json()
        
        # Verify navigation worked
        assert subdir_data['path'] == first_dir['path']
        assert subdir_data['parent'] == root_data['path']
    
    def test_size_calculations_consistency(self):
        """Test that size calculations are consistent"""
        response = self.client.get('/api/analyze')
        root_data = response.json()
        
        # Sum of individual item sizes should equal total size
        calculated_total = sum(item['size'] for item in root_data['items'])
        assert calculated_total == root_data['total_size']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
