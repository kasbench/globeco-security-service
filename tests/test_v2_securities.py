import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.security import Security
from app.models.security_type import SecurityType
from bson import ObjectId

client = TestClient(app)

class TestV2SecuritiesAPI:
    """Test suite for v2 securities search API"""

    def test_search_all_securities_default_pagination(self):
        """Test getting all securities with default pagination"""
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
        response = client.get("/api/v2/securities?ticker=AAPL")
        assert response.status_code == 200
        
        data = response.json()
        securities = data["securities"]
        
        # All results should have ticker matching AAPL (case-insensitive)
        for security in securities:
            assert security["ticker"].upper() == "AAPL"

    def test_search_partial_ticker(self):
        """Test partial ticker search"""
        response = client.get("/api/v2/securities?ticker_like=APP")
        assert response.status_code == 200
        
        data = response.json()
        securities = data["securities"]
        
        # All results should contain "APP" in ticker (case-insensitive)
        for security in securities:
            assert "APP" in security["ticker"].upper()

    def test_pagination_parameters(self):
        """Test pagination with custom limit and offset"""
        response = client.get("/api/v2/securities?limit=5&offset=10")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["securities"]) <= 5
        assert data["pagination"]["pageSize"] == 5
        assert data["pagination"]["currentPage"] == 2  # offset 10 / limit 5

    def test_mutual_exclusivity_validation(self):
        """Test that ticker and ticker_like cannot be used together"""
        response = client.get("/api/v2/securities?ticker=AAPL&ticker_like=APP")
        assert response.status_code == 400
        
        error_detail = response.json()["detail"]
        assert "Only one of 'ticker' or 'ticker_like' parameters can be provided" in error_detail

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
        response = client.get("/api/v2/securities?limit=1")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check main structure
        assert "securities" in data
        assert "pagination" in data
        
        # Check security structure if any securities exist
        if data["securities"]:
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
        # Test with lowercase
        response1 = client.get("/api/v2/securities?ticker=aapl")
        # Test with uppercase
        response2 = client.get("/api/v2/securities?ticker=AAPL")
        # Test with mixed case
        response3 = client.get("/api/v2/securities?ticker=AaPl")
        
        # All should return same results (assuming AAPL exists)
        if response1.status_code == 200 and response2.status_code == 200 and response3.status_code == 200:
            data1 = response1.json()
            data2 = response2.json()
            data3 = response3.json()
            
            assert len(data1["securities"]) == len(data2["securities"]) == len(data3["securities"])

    def test_result_ordering(self):
        """Test that results are ordered by ticker alphabetically"""
        response = client.get("/api/v2/securities?limit=100")
        assert response.status_code == 200
        
        data = response.json()
        securities = data["securities"]
        
        if len(securities) > 1:
            # Check that tickers are in alphabetical order
            tickers = [sec["ticker"] for sec in securities]
            assert tickers == sorted(tickers)

    def test_no_results_found(self):
        """Test response when no securities match the search"""
        response = client.get("/api/v2/securities?ticker=NONEXISTENT_TICKER_12345")
        assert response.status_code == 200
        
        data = response.json()
        assert data["securities"] == []
        assert data["pagination"]["totalElements"] == 0
        assert data["pagination"]["totalPages"] == 0

    def test_backward_compatibility_v1_unchanged(self):
        """Test that v1 API remains unchanged"""
        # Test v1 securities endpoint
        v1_response = client.get("/api/v1/securities")
        
        # Should still work and return list format (not paginated)
        if v1_response.status_code == 200:
            v1_data = v1_response.json()
            assert isinstance(v1_data, list)  # v1 returns list, not paginated object
            
            # If there are securities, check structure matches v1 format
            if v1_data:
                security = v1_data[0]
                required_fields = ["securityId", "ticker", "description", "securityTypeId", "version", "securityType"]
                for field in required_fields:
                    assert field in security 