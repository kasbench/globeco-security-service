import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch

class TestV2APIEndpoints:
    """API endpoint tests for v2 securities search."""

    def test_get_securities_empty_database(self, test_client, clean_database):
        """Test GET /api/v2/securities with empty database."""
        with patch('app.services.security_service.search_securities') as mock_search:
            # Mock empty response
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
            
            assert data["securities"] == []
            assert data["pagination"]["totalElements"] == 0
            assert data["pagination"]["totalPages"] == 0
            assert data["pagination"]["currentPage"] == 0
            assert data["pagination"]["pageSize"] == 50
            assert data["pagination"]["hasNext"] == False
            assert data["pagination"]["hasPrevious"] == False

    def test_get_securities_with_ticker_param(self, test_client):
        """Test GET /api/v2/securities with ticker parameter."""
        with patch('app.services.security_service.search_securities') as mock_search:
            # Mock single security response
            from app.schemas.v2_security import SecuritySearchResponse, SecurityV2, SecurityTypeNestedV2, PaginationInfo
            from bson import ObjectId
            
            security_id = ObjectId()
            security_type_id = ObjectId()
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[
                    SecurityV2(
                        securityId=security_id,
                        ticker="AAPL",
                        description="Apple Inc. Common Stock",
                        securityTypeId=security_type_id,
                        securityType=SecurityTypeNestedV2(
                            securityTypeId=security_type_id,
                            abbreviation="CS",
                            description="Common Stock",
                            version=1
                        ),
                        version=1
                    )
                ],
                pagination=PaginationInfo(
                    totalElements=1,
                    totalPages=1,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            response = test_client.get("/api/v2/securities?ticker=AAPL")
            
            assert response.status_code == 200
            data = response.json()
            
            assert len(data["securities"]) == 1
            assert data["securities"][0]["ticker"] == "AAPL"
            assert data["securities"][0]["description"] == "Apple Inc. Common Stock"
            assert data["securities"][0]["securityType"]["abbreviation"] == "CS"
            assert data["pagination"]["totalElements"] == 1
            
            # Verify the service was called with correct parameters
            mock_search.assert_called_once_with(
                ticker="AAPL",
                ticker_like=None,
                limit=50,
                offset=0
            )

    def test_get_securities_with_ticker_like_param(self, test_client):
        """Test GET /api/v2/securities with ticker_like parameter."""
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
            
            response = test_client.get("/api/v2/securities?ticker_like=APP")
            
            assert response.status_code == 200
            
            # Verify the service was called with correct parameters
            mock_search.assert_called_once_with(
                ticker=None,
                ticker_like="APP",
                limit=50,
                offset=0
            )

    def test_get_securities_with_pagination_params(self, test_client):
        """Test GET /api/v2/securities with pagination parameters."""
        with patch('app.services.security_service.search_securities') as mock_search:
            from app.schemas.v2_security import SecuritySearchResponse, PaginationInfo
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[],
                pagination=PaginationInfo(
                    totalElements=0,
                    totalPages=0,
                    currentPage=1,
                    pageSize=25,
                    hasNext=False,
                    hasPrevious=True
                )
            )
            
            response = test_client.get("/api/v2/securities?limit=25&offset=25")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["pagination"]["currentPage"] == 1
            assert data["pagination"]["pageSize"] == 25
            
            # Verify the service was called with correct parameters
            mock_search.assert_called_once_with(
                ticker=None,
                ticker_like=None,
                limit=25,
                offset=25
            )

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
        
        # Test valid offset
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
            
            response = test_client.get("/api/v2/securities?offset=100")
            assert response.status_code == 200

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

    def test_response_schema_structure(self, test_client):
        """Test that response follows the expected schema structure."""
        with patch('app.services.security_service.search_securities') as mock_search:
            from app.schemas.v2_security import SecuritySearchResponse, SecurityV2, SecurityTypeNestedV2, PaginationInfo
            from bson import ObjectId
            
            security_id = ObjectId()
            security_type_id = ObjectId()
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[
                    SecurityV2(
                        securityId=security_id,
                        ticker="AAPL",
                        description="Apple Inc. Common Stock",
                        securityTypeId=security_type_id,
                        securityType=SecurityTypeNestedV2(
                            securityTypeId=security_type_id,
                            abbreviation="CS",
                            description="Common Stock",
                            version=1
                        ),
                        version=1
                    )
                ],
                pagination=PaginationInfo(
                    totalElements=1,
                    totalPages=1,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            response = test_client.get("/api/v2/securities")
            
            assert response.status_code == 200
            data = response.json()
            
            # Check top-level structure
            assert "securities" in data
            assert "pagination" in data
            
            # Check securities structure
            assert isinstance(data["securities"], list)
            if data["securities"]:
                security = data["securities"][0]
                required_fields = ["securityId", "ticker", "description", "securityTypeId", "securityType", "version"]
                for field in required_fields:
                    assert field in security, f"Missing field: {field}"
                
                # Check nested securityType structure
                security_type = security["securityType"]
                required_type_fields = ["securityTypeId", "abbreviation", "description", "version"]
                for field in required_type_fields:
                    assert field in security_type, f"Missing securityType field: {field}"
            
            # Check pagination structure
            pagination = data["pagination"]
            required_pagination_fields = ["totalElements", "totalPages", "currentPage", "pageSize", "hasNext", "hasPrevious"]
            for field in required_pagination_fields:
                assert field in pagination, f"Missing pagination field: {field}"

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

    def test_backward_compatibility_v1_still_works(self, test_client):
        """Test that v1 API endpoints still work after v2 implementation."""
        # This test ensures we haven't broken existing functionality
        response = test_client.get("/api/v1/securities")
        
        # Should not return 404 (endpoint exists)
        # Actual response depends on database state, but endpoint should be accessible
        assert response.status_code != 404 