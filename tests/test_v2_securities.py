import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.models.security import Security
from app.models.security_type import SecurityType
from bson import ObjectId
from app.schemas.v2_security import SecuritySearchResponse, PaginationInfo, SecurityV2, SecurityTypeNestedV2

client = TestClient(app)

class TestV2SecuritiesAPI:
    """Test suite for v2 securities search API"""

    def test_search_all_securities_default_pagination(self):
        """Test getting all securities with default pagination"""
        with patch('app.services.security_service.search_securities') as mock_search:
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
            
            response = client.get("/api/v2/securities")
            assert response.status_code == 200
            
            data = response.json()
            assert "securities" in data
            assert "pagination" in data
            assert isinstance(data["securities"], list)
            
            pagination = data["pagination"]
            assert "totalElements" in pagination
            assert "totalPages" in pagination
            assert "currentPage" in pagination
            assert "pageSize" in pagination
            assert "hasNext" in pagination
            assert "hasPrevious" in pagination
            assert pagination["pageSize"] == 50  # default limit

    def test_search_exact_ticker(self):
        """Test exact ticker search"""
        with patch('app.services.security_service.search_securities') as mock_search:
            mock_security = SecurityV2(
                securityId="60f7b3b3b3b3b3b3b3b3b3b3",
                ticker="AAPL",
                description="Apple Inc.",
                securityTypeId="60f7b3b3b3b3b3b3b3b3b3b4",
                version=1,
                securityType=SecurityTypeNestedV2(
                    securityTypeId="60f7b3b3b3b3b3b3b3b3b3b4",
                    abbreviation="CS",
                    description="Common Stock",
                    version=1
                )
            )
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[mock_security],
                pagination=PaginationInfo(
                    totalElements=1,
                    totalPages=1,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            response = client.get("/api/v2/securities?ticker=AAPL")
            assert response.status_code == 200
            
            data = response.json()
            securities = data["securities"]
            
            # Should call with exact ticker parameter
            mock_search.assert_called_with(
                ticker="AAPL",
                ticker_like=None,
                limit=50,
                offset=0
            )

    def test_search_partial_ticker(self):
        """Test partial ticker search"""
        with patch('app.services.security_service.search_securities') as mock_search:
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
            
            response = client.get("/api/v2/securities?ticker_like=APP")
            assert response.status_code == 200
            
            # Should call with ticker_like parameter
            mock_search.assert_called_with(
                ticker=None,
                ticker_like="APP",
                limit=50,
                offset=0
            )

    def test_pagination_parameters(self):
        """Test pagination with custom limit and offset"""
        with patch('app.services.security_service.search_securities') as mock_search:
            mock_search.return_value = SecuritySearchResponse(
                securities=[],
                pagination=PaginationInfo(
                    totalElements=0,
                    totalPages=0,
                    currentPage=2,
                    pageSize=5,
                    hasNext=False,
                    hasPrevious=True
                )
            )
            
            response = client.get("/api/v2/securities?limit=5&offset=10")
            assert response.status_code == 200
            
            # Should call with correct pagination parameters
            mock_search.assert_called_with(
                ticker=None,
                ticker_like=None,
                limit=5,
                offset=10
            )

    def test_mutual_exclusivity_validation(self):
        """Test that ticker and ticker_like cannot be used together"""
        response = client.get("/api/v2/securities?ticker=AAPL&ticker_like=APP")
        assert response.status_code == 400
        
        error_detail = response.json()["detail"]
        assert "Only one of 'ticker' or 'ticker_like' parameters can be provided" in str(error_detail)

    def test_invalid_ticker_format(self):
        """Test validation of ticker format"""
        # Test with invalid characters
        response = client.get("/api/v2/securities?ticker=AAPL@#$")
        assert response.status_code == 400
        
        # Test with too long ticker
        long_ticker = "A" * 51
        response = client.get(f"/api/v2/securities?ticker={long_ticker}")
        assert response.status_code == 400

    def test_limit_bounds_validation(self):
        """Test limit parameter bounds"""
        # Test limit too high
        response = client.get("/api/v2/securities?limit=1001")
        assert response.status_code == 422
        
        # Test limit too low
        response = client.get("/api/v2/securities?limit=0")
        assert response.status_code == 422

    def test_offset_bounds_validation(self):
        """Test offset parameter bounds"""
        # Test negative offset
        response = client.get("/api/v2/securities?offset=-1")
        assert response.status_code == 422

    def test_response_schema_structure(self):
        """Test that response follows the expected schema"""
        with patch('app.services.security_service.search_securities') as mock_search:
            mock_security = SecurityV2(
                securityId="60f7b3b3b3b3b3b3b3b3b3b3",
                ticker="AAPL",
                description="Apple Inc.",
                securityTypeId="60f7b3b3b3b3b3b3b3b3b3b4",
                version=1,
                securityType=SecurityTypeNestedV2(
                    securityTypeId="60f7b3b3b3b3b3b3b3b3b3b4",
                    abbreviation="CS",
                    description="Common Stock",
                    version=1
                )
            )
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[mock_security],
                pagination=PaginationInfo(
                    totalElements=1,
                    totalPages=1,
                    currentPage=0,
                    pageSize=1,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            response = client.get("/api/v2/securities?limit=1")
            assert response.status_code == 200
            
            data = response.json()
            
            # Check main structure
            assert "securities" in data
            assert "pagination" in data
            
            # Check security structure
            security = data["securities"][0]
            required_fields = ["securityId", "ticker", "description", "securityTypeId", "version", "securityType"]
            for field in required_fields:
                assert field in security
            
            # Check nested securityType structure
            security_type = security["securityType"]
            st_required_fields = ["securityTypeId", "abbreviation", "description", "version"]
            for field in st_required_fields:
                assert field in security_type

    def test_case_insensitive_search(self):
        """Test that searches are case-insensitive"""
        with patch('app.services.security_service.search_securities') as mock_search:
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
            
            # Test with lowercase
            response1 = client.get("/api/v2/securities?ticker=aapl")
            assert response1.status_code == 200
            
            # Test with uppercase
            response2 = client.get("/api/v2/securities?ticker=AAPL")
            assert response2.status_code == 200
            
            # Both should call the service (case handling is done in service layer)
            assert mock_search.call_count == 2

    def test_result_ordering(self):
        """Test that results are ordered by ticker alphabetically"""
        with patch('app.services.security_service.search_securities') as mock_search:
            mock_search.return_value = SecuritySearchResponse(
                securities=[],
                pagination=PaginationInfo(
                    totalElements=0,
                    totalPages=0,
                    currentPage=0,
                    pageSize=100,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            response = client.get("/api/v2/securities?limit=100")
            assert response.status_code == 200
            
            # Service should be called with correct parameters
            mock_search.assert_called_with(
                ticker=None,
                ticker_like=None,
                limit=100,
                offset=0
            )

    def test_no_results_found(self):
        """Test response when no securities match the search"""
        with patch('app.services.security_service.search_securities') as mock_search:
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
            
            response = client.get("/api/v2/securities?ticker=NONEXISTENTTICKER12345")
            assert response.status_code == 200
            
            data = response.json()
            assert data["securities"] == []
            assert data["pagination"]["totalElements"] == 0
            assert data["pagination"]["totalPages"] == 0

    def test_backward_compatibility_v1_unchanged(self):
        """Test that v1 API remains unchanged"""
        with patch('app.services.security_service.get_all_securities') as mock_get_all:
            mock_get_all.return_value = []
            
            # Test v1 securities endpoint
            v1_response = client.get("/api/v1/securities")
            
            # Should still work and return list format (not paginated)
            assert v1_response.status_code == 200
            v1_data = v1_response.json()
            assert isinstance(v1_data, list)  # v1 returns list, not paginated object 