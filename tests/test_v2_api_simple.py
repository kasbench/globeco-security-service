import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

class TestV2APISimple:
    """Simplified API tests for v2 securities search without database integration."""

    @pytest.fixture
    def test_client(self):
        """Create FastAPI test client."""
        return TestClient(app)

    def test_mutual_exclusivity_validation(self, test_client):
        """Test that ticker and ticker_like are mutually exclusive."""
        response = test_client.get("/api/v2/securities?ticker=AAPL&ticker_like=APP")
        
        assert response.status_code == 400
        data = response.json()
        assert "Only one of 'ticker' or 'ticker_like' parameters can be provided" in data["detail"]

    def test_ticker_format_validation(self, test_client):
        """Test ticker format validation."""
        # Test empty ticker
        response = test_client.get("/api/v2/securities?ticker=")
        assert response.status_code == 400
        
        # Test ticker too long (over 50 characters)
        long_ticker = "A" * 51
        response = test_client.get(f"/api/v2/securities?ticker={long_ticker}")
        assert response.status_code == 400
        
        # Test ticker with invalid characters
        response = test_client.get("/api/v2/securities?ticker=AAPL@#$")
        assert response.status_code == 400

    def test_ticker_like_format_validation(self, test_client):
        """Test ticker_like format validation."""
        # Test empty ticker_like
        response = test_client.get("/api/v2/securities?ticker_like=")
        assert response.status_code == 400
        
        # Test ticker_like too long (over 50 characters)
        long_ticker = "A" * 51
        response = test_client.get(f"/api/v2/securities?ticker_like={long_ticker}")
        assert response.status_code == 400

    def test_limit_validation(self, test_client):
        """Test limit parameter validation."""
        # Test limit too small
        response = test_client.get("/api/v2/securities?limit=0")
        assert response.status_code == 422  # FastAPI validation error
        
        # Test limit too large
        response = test_client.get("/api/v2/securities?limit=1001")
        assert response.status_code == 422  # FastAPI validation error
        
        # Test negative limit
        response = test_client.get("/api/v2/securities?limit=-1")
        assert response.status_code == 422  # FastAPI validation error

    def test_offset_validation(self, test_client):
        """Test offset parameter validation."""
        # Test negative offset
        response = test_client.get("/api/v2/securities?offset=-1")
        assert response.status_code == 422  # FastAPI validation error

    def test_valid_ticker_formats(self, test_client):
        """Test various valid ticker formats."""
        valid_tickers = [
            "AAPL",           # Standard ticker
            "BRK.A",          # With dot
            "BRK-A",          # With hyphen
            "A",              # Single character
            "ABCDEFGHIJ",     # 10 characters
            "ABC123",         # With numbers
            "ABC.TO",         # Exchange suffix
        ]
        
        with patch('app.services.security_service.search_securities') as mock_search:
            from app.schemas.v2_security import SecuritySearchResponse, PaginationInfo
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[],
                pagination=PaginationInfo(
                    totalElements=0,
                    totalPages=0,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            for ticker in valid_tickers:
                response = test_client.get(f"/api/v2/securities?ticker={ticker}")
                assert response.status_code == 200, f"Failed for ticker: {ticker}"

    def test_api_endpoint_exists(self, test_client):
        """Test that the v2 API endpoint exists and is accessible."""
        with patch('app.services.security_service.search_securities') as mock_search:
            from app.schemas.v2_security import SecuritySearchResponse, PaginationInfo
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[],
                pagination=PaginationInfo(
                    totalElements=0,
                    totalPages=0,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            response = test_client.get("/api/v2/securities")
            assert response.status_code == 200
            
            data = response.json()
            assert "securities" in data
            assert "pagination" in data

    def test_service_call_parameters(self, test_client):
        """Test that the service is called with correct parameters."""
        with patch('app.services.security_service.search_securities') as mock_search:
            from app.schemas.v2_security import SecuritySearchResponse, PaginationInfo
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[],
                pagination=PaginationInfo(
                    totalElements=0,
                    totalPages=0,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            # Test with ticker parameter
            test_client.get("/api/v2/securities?ticker=AAPL")
            mock_search.assert_called_with(
                ticker="AAPL",
                ticker_like=None,
                limit=50,
                offset=0
            )
            
            # Test with ticker_like parameter
            mock_search.reset_mock()
            test_client.get("/api/v2/securities?ticker_like=APP")
            mock_search.assert_called_with(
                ticker=None,
                ticker_like="APP",
                limit=50,
                offset=0
            )
            
            # Test with pagination parameters
            mock_search.reset_mock()
            test_client.get("/api/v2/securities?limit=25&offset=25")
            mock_search.assert_called_with(
                ticker=None,
                ticker_like=None,
                limit=25,
                offset=25
            )

    def test_api_documentation_accessibility(self, test_client):
        """Test that the API endpoint is properly documented in OpenAPI."""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_spec = response.json()
        
        # Check that our v2 endpoint is documented
        assert "/api/v2/securities" in openapi_spec["paths"]
        
        securities_endpoint = openapi_spec["paths"]["/api/v2/securities"]["get"]
        
        # Check parameters are documented
        parameter_names = [param["name"] for param in securities_endpoint["parameters"]]
        expected_params = ["ticker", "ticker_like", "limit", "offset"]
        
        for param in expected_params:
            assert param in parameter_names, f"Parameter {param} not documented"

    def test_case_insensitive_search_via_api(self, test_client):
        """Test case-insensitive search through API endpoint."""
        with patch('app.services.security_service.search_securities') as mock_search:
            from app.schemas.v2_security import SecuritySearchResponse, PaginationInfo
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[],
                pagination=PaginationInfo(
                    totalElements=0,
                    totalPages=0,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            # Test lowercase ticker
            response = test_client.get("/api/v2/securities?ticker=aapl")
            assert response.status_code == 200
            
            # Test mixed case ticker_like
            response = test_client.get("/api/v2/securities?ticker_like=ApP")
            assert response.status_code == 200 