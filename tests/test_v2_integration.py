import pytest
from app.services import security_service
from app.schemas.v2_security import SecuritySearchParams

class TestV2SecuritiesIntegration:
    """Integration tests for v2 securities search with real MongoDB."""

    @pytest.mark.asyncio
    async def test_search_all_securities_empty_database(self, clean_database):
        """Test searching in empty database returns empty results."""
        result = await security_service.search_securities()
        
        assert result.securities == []
        assert result.pagination.totalElements == 0
        assert result.pagination.totalPages == 0
        assert result.pagination.currentPage == 0
        assert result.pagination.pageSize == 50
        assert result.pagination.hasNext == False
        assert result.pagination.hasPrevious == False

    @pytest.mark.asyncio
    async def test_search_all_securities_with_data(self, sample_securities):
        """Test searching all securities with sample data."""
        result = await security_service.search_securities()
        
        assert len(result.securities) == 8  # All sample securities
        assert result.pagination.totalElements == 8
        assert result.pagination.totalPages == 1
        assert result.pagination.currentPage == 0
        assert result.pagination.pageSize == 50
        assert result.pagination.hasNext == False
        assert result.pagination.hasPrevious == False
        
        # Check that results are ordered by ticker
        tickers = [sec.ticker for sec in result.securities]
        assert tickers == sorted(tickers)

    @pytest.mark.asyncio
    async def test_exact_ticker_search(self, sample_securities):
        """Test exact ticker search functionality."""
        # Test existing ticker
        result = await security_service.search_securities(ticker="AAPL")
        
        assert len(result.securities) == 1
        assert result.securities[0].ticker == "AAPL"
        assert result.securities[0].description == "Apple Inc. Common Stock"
        assert result.pagination.totalElements == 1
        
        # Test non-existing ticker
        result = await security_service.search_securities(ticker="NONEXISTENT")
        assert len(result.securities) == 0
        assert result.pagination.totalElements == 0

    @pytest.mark.asyncio
    async def test_case_insensitive_exact_search(self, sample_securities):
        """Test that exact ticker search is case-insensitive."""
        # Test lowercase
        result_lower = await security_service.search_securities(ticker="aapl")
        # Test uppercase
        result_upper = await security_service.search_securities(ticker="AAPL")
        # Test mixed case
        result_mixed = await security_service.search_securities(ticker="AaPl")
        
        # All should return the same result
        assert len(result_lower.securities) == 1
        assert len(result_upper.securities) == 1
        assert len(result_mixed.securities) == 1
        
        assert result_lower.securities[0].ticker == "AAPL"
        assert result_upper.securities[0].ticker == "AAPL"
        assert result_mixed.securities[0].ticker == "AAPL"

    @pytest.mark.asyncio
    async def test_partial_ticker_search(self, sample_securities):
        """Test partial ticker search functionality."""
        # Search for tickers containing "APP"
        result = await security_service.search_securities(ticker_like="APP")
        
        # Should find AAPL, APPN, APP.TO, AAPL.PF
        assert len(result.securities) == 4
        tickers = [sec.ticker for sec in result.securities]
        assert "AAPL" in tickers
        assert "APPN" in tickers
        assert "APP.TO" in tickers
        assert "AAPL.PF" in tickers
        
        # Results should be ordered alphabetically
        assert tickers == sorted(tickers)

    @pytest.mark.asyncio
    async def test_case_insensitive_partial_search(self, sample_securities):
        """Test that partial ticker search is case-insensitive."""
        # Test lowercase
        result_lower = await security_service.search_securities(ticker_like="app")
        # Test uppercase
        result_upper = await security_service.search_securities(ticker_like="APP")
        # Test mixed case
        result_mixed = await security_service.search_securities(ticker_like="ApP")
        
        # All should return the same results
        assert len(result_lower.securities) == len(result_upper.securities) == len(result_mixed.securities)
        
        lower_tickers = [sec.ticker for sec in result_lower.securities]
        upper_tickers = [sec.ticker for sec in result_upper.securities]
        mixed_tickers = [sec.ticker for sec in result_mixed.securities]
        
        assert lower_tickers == upper_tickers == mixed_tickers

    @pytest.mark.asyncio
    async def test_pagination_functionality(self, sample_securities):
        """Test pagination with limit and offset."""
        # Test first page with limit 3
        result_page1 = await security_service.search_securities(limit=3, offset=0)
        
        assert len(result_page1.securities) == 3
        assert result_page1.pagination.totalElements == 8
        assert result_page1.pagination.totalPages == 3  # ceil(8/3)
        assert result_page1.pagination.currentPage == 0
        assert result_page1.pagination.pageSize == 3
        assert result_page1.pagination.hasNext == True
        assert result_page1.pagination.hasPrevious == False
        
        # Test second page
        result_page2 = await security_service.search_securities(limit=3, offset=3)
        
        assert len(result_page2.securities) == 3
        assert result_page2.pagination.currentPage == 1
        assert result_page2.pagination.hasNext == True
        assert result_page2.pagination.hasPrevious == True
        
        # Test last page
        result_page3 = await security_service.search_securities(limit=3, offset=6)
        
        assert len(result_page3.securities) == 2  # Only 2 remaining
        assert result_page3.pagination.currentPage == 2
        assert result_page3.pagination.hasNext == False
        assert result_page3.pagination.hasPrevious == True
        
        # Ensure no overlap between pages
        page1_tickers = [sec.ticker for sec in result_page1.securities]
        page2_tickers = [sec.ticker for sec in result_page2.securities]
        page3_tickers = [sec.ticker for sec in result_page3.securities]
        
        assert len(set(page1_tickers) & set(page2_tickers)) == 0
        assert len(set(page2_tickers) & set(page3_tickers)) == 0
        assert len(set(page1_tickers) & set(page3_tickers)) == 0

    @pytest.mark.asyncio
    async def test_pagination_with_search(self, sample_securities):
        """Test pagination combined with search functionality."""
        # Search for "A" with pagination (should find AAPL, AMZN, APPN, APP.TO, AAPL.PF)
        result = await security_service.search_securities(ticker_like="A", limit=2, offset=0)
        
        assert len(result.securities) == 2
        assert result.pagination.totalElements == 5
        assert result.pagination.totalPages == 3  # ceil(5/2)
        assert result.pagination.hasNext == True
        
        # All results should contain "A"
        for security in result.securities:
            assert "A" in security.ticker.upper()

    @pytest.mark.asyncio
    async def test_security_type_population(self, sample_securities):
        """Test that security type information is properly populated."""
        result = await security_service.search_securities(ticker="AAPL")
        
        assert len(result.securities) == 1
        security = result.securities[0]
        
        # Check security fields
        assert security.securityId is not None
        assert security.ticker == "AAPL"
        assert security.description == "Apple Inc. Common Stock"
        assert security.securityTypeId is not None
        assert security.version == 1
        
        # Check nested security type
        assert security.securityType is not None
        assert security.securityType.securityTypeId == security.securityTypeId
        assert security.securityType.abbreviation == "CS"
        assert security.securityType.description == "Common Stock"
        assert security.securityType.version == 1

    @pytest.mark.asyncio
    async def test_result_ordering(self, sample_securities):
        """Test that results are consistently ordered by ticker."""
        result = await security_service.search_securities()
        
        tickers = [sec.ticker for sec in result.securities]
        expected_order = ["AAPL", "AAPL.PF", "AMZN", "APP.TO", "APPN", "GOOGL", "MSFT", "TSLA"]
        
        assert tickers == expected_order

    @pytest.mark.asyncio
    async def test_edge_case_empty_search(self, sample_securities):
        """Test edge case with search that returns no results."""
        result = await security_service.search_securities(ticker_like="XYZ123")
        
        assert result.securities == []
        assert result.pagination.totalElements == 0
        assert result.pagination.totalPages == 0
        assert result.pagination.hasNext == False
        assert result.pagination.hasPrevious == False

    @pytest.mark.asyncio
    async def test_edge_case_large_offset(self, sample_securities):
        """Test edge case with offset larger than total results."""
        result = await security_service.search_securities(offset=100)
        
        assert result.securities == []
        assert result.pagination.totalElements == 8
        assert result.pagination.currentPage == 2  # 100 // 50
        assert result.pagination.hasNext == False
        assert result.pagination.hasPrevious == True

    @pytest.mark.asyncio
    async def test_special_characters_in_ticker(self, sample_securities):
        """Test searching for tickers with special characters."""
        # Search for ticker with dot
        result = await security_service.search_securities(ticker="APP.TO")
        
        assert len(result.securities) == 1
        assert result.securities[0].ticker == "APP.TO"
        
        # Partial search should also work
        result = await security_service.search_securities(ticker_like=".TO")
        assert len(result.securities) == 1
        assert result.securities[0].ticker == "APP.TO"

    @pytest.mark.asyncio
    async def test_performance_large_limit(self, sample_securities):
        """Test performance with maximum allowed limit."""
        result = await security_service.search_securities(limit=1000)
        
        assert len(result.securities) == 8  # All available securities
        assert result.pagination.pageSize == 1000
        assert result.pagination.totalElements == 8 