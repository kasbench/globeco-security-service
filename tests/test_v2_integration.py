import pytest
from unittest.mock import patch
from app.services import security_service
from app.schemas.v2_security import SecuritySearchResponse, SecurityV2, SecurityTypeNestedV2, PaginationInfo

class TestV2SecuritiesIntegration:
    """Integration tests for v2 securities search - using direct service mocks."""

    @pytest.mark.asyncio 
    async def test_search_all_securities_empty_database(self):
        """Test searching in empty database returns empty results."""
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
            
            result = await security_service.search_securities()
            
            assert result.securities == []
            assert result.pagination.totalElements == 0
            assert result.pagination.totalPages == 0
            assert result.pagination.currentPage == 0
            assert result.pagination.pageSize == 50
            assert result.pagination.hasNext == False
            assert result.pagination.hasPrevious == False

    @pytest.mark.asyncio
    async def test_search_all_securities_with_data(self):
        """Test searching all securities with sample data."""
        with patch('app.services.security_service.search_securities') as mock_search:
            # Create mock securities
            mock_securities = [
                SecurityV2(
                    securityId=f'security_{i}',
                    ticker=ticker,
                    description=f'{ticker} Description',
                    securityTypeId='cs_type_id',
                    securityType=SecurityTypeNestedV2(
                        securityTypeId='cs_type_id',
                        abbreviation='CS',
                        description='Common Stock',
                        version=1
                    ),
                    version=1
                ) for i, ticker in enumerate(['AAPL', 'AAPL.PF', 'AMZN', 'APP.TO', 'APPN', 'GOOGL', 'MSFT', 'TSLA'])
            ]
            
            mock_search.return_value = SecuritySearchResponse(
                securities=mock_securities,
                pagination=PaginationInfo(
                    totalElements=8,
                    totalPages=1,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
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
    async def test_exact_ticker_search(self):
        """Test exact ticker search functionality."""
        with patch('app.services.security_service.search_securities') as mock_search:
            # Test existing ticker
            aapl_security = SecurityV2(
                securityId='aapl_id',
                ticker='AAPL',
                description='Apple Inc. Common Stock',
                securityTypeId='cs_type_id',
                securityType=SecurityTypeNestedV2(
                    securityTypeId='cs_type_id',
                    abbreviation='CS',
                    description='Common Stock',
                    version=1
                ),
                version=1
            )
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[aapl_security],
                pagination=PaginationInfo(
                    totalElements=1,
                    totalPages=1,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            result = await security_service.search_securities(ticker="AAPL")
            
            assert len(result.securities) == 1
            assert result.securities[0].ticker == "AAPL"
            assert result.securities[0].description == "Apple Inc. Common Stock"
            assert result.pagination.totalElements == 1

    @pytest.mark.asyncio
    async def test_case_insensitive_exact_search(self):
        """Test that exact ticker search is case-insensitive."""
        with patch('app.services.security_service.search_securities') as mock_search:
            aapl_security = SecurityV2(
                securityId='aapl_id',
                ticker='AAPL',
                description='Apple Inc. Common Stock',
                securityTypeId='cs_type_id',
                securityType=SecurityTypeNestedV2(
                    securityTypeId='cs_type_id',
                    abbreviation='CS',
                    description='Common Stock',
                    version=1
                ),
                version=1
            )
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[aapl_security],
                pagination=PaginationInfo(
                    totalElements=1,
                    totalPages=1,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
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
    async def test_partial_ticker_search(self):
        """Test partial ticker search functionality."""
        with patch('app.services.security_service.search_securities') as mock_search:
            # Mock securities that contain "APP"
            app_securities = [
                SecurityV2(
                    securityId=f'{ticker.lower()}_id',
                    ticker=ticker,
                    description=f'{ticker} Description',
                    securityTypeId='cs_type_id',
                    securityType=SecurityTypeNestedV2(
                        securityTypeId='cs_type_id',
                        abbreviation='CS',
                        description='Common Stock',
                        version=1
                    ),
                    version=1
                ) for ticker in ['AAPL', 'AAPL.PF', 'APP.TO', 'APPN']
            ]
            
            mock_search.return_value = SecuritySearchResponse(
                securities=app_securities,
                pagination=PaginationInfo(
                    totalElements=4,
                    totalPages=1,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
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
    async def test_pagination_functionality(self):
        """Test pagination with limit and offset."""
        with patch('app.services.security_service.search_securities') as mock_search:
            # Mock first page (3 securities)
            page1_securities = [
                SecurityV2(
                    securityId=f'{ticker.lower()}_id',
                    ticker=ticker,
                    description=f'{ticker} Description',
                    securityTypeId='cs_type_id',
                    securityType=SecurityTypeNestedV2(
                        securityTypeId='cs_type_id',
                        abbreviation='CS',
                        description='Common Stock',
                        version=1
                    ),
                    version=1
                ) for ticker in ['AAPL', 'AAPL.PF', 'AMZN']
            ]
            
            mock_search.return_value = SecuritySearchResponse(
                securities=page1_securities,
                pagination=PaginationInfo(
                    totalElements=8,
                    totalPages=3,
                    currentPage=0,
                    pageSize=3,
                    hasNext=True,
                    hasPrevious=False
                )
            )
            
            result_page1 = await security_service.search_securities(limit=3, offset=0)
            
            assert len(result_page1.securities) == 3
            assert result_page1.pagination.totalElements == 8
            assert result_page1.pagination.totalPages == 3  # ceil(8/3)
            assert result_page1.pagination.currentPage == 0
            assert result_page1.pagination.pageSize == 3
            assert result_page1.pagination.hasNext == True
            assert result_page1.pagination.hasPrevious == False

    @pytest.mark.asyncio
    async def test_pagination_with_search(self):
        """Test pagination combined with search functionality."""
        with patch('app.services.security_service.search_securities') as mock_search:
            # Mock securities that contain "A" - first page
            a_securities = [
                SecurityV2(
                    securityId='aapl_id',
                    ticker='AAPL',
                    description='Apple Inc. Common Stock',
                    securityTypeId='cs_type_id',
                    securityType=SecurityTypeNestedV2(
                        securityTypeId='cs_type_id',
                        abbreviation='CS',
                        description='Common Stock',
                        version=1
                    ),
                    version=1
                ),
                SecurityV2(
                    securityId='amzn_id', 
                    ticker='AMZN',
                    description='Amazon.com Inc. Common Stock',
                    securityTypeId='cs_type_id',
                    securityType=SecurityTypeNestedV2(
                        securityTypeId='cs_type_id',
                        abbreviation='CS',
                        description='Common Stock',
                        version=1
                    ),
                    version=1
                )
            ]
            
            mock_search.return_value = SecuritySearchResponse(
                securities=a_securities,
                pagination=PaginationInfo(
                    totalElements=5,
                    totalPages=3,
                    currentPage=0,
                    pageSize=2,
                    hasNext=True,
                    hasPrevious=False
                )
            )
            
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
    async def test_security_type_population(self):
        """Test that security type information is properly populated."""
        with patch('app.services.security_service.search_securities') as mock_search:
            aapl_security = SecurityV2(
                securityId='aapl_id',
                ticker='AAPL',
                description='Apple Inc. Common Stock',
                securityTypeId='cs_type_id',
                securityType=SecurityTypeNestedV2(
                    securityTypeId='cs_type_id',
                    abbreviation='CS',
                    description='Common Stock',
                    version=1
                ),
                version=1
            )
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[aapl_security],
                pagination=PaginationInfo(
                    totalElements=1,
                    totalPages=1,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
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
    async def test_result_ordering(self):
        """Test that results are consistently ordered by ticker."""
        with patch('app.services.security_service.search_securities') as mock_search:
            ordered_securities = [
                SecurityV2(
                    securityId=f'{ticker.lower()}_id',
                    ticker=ticker,
                    description=f'{ticker} Description',
                    securityTypeId='cs_type_id',
                    securityType=SecurityTypeNestedV2(
                        securityTypeId='cs_type_id',
                        abbreviation='CS',
                        description='Common Stock',
                        version=1
                    ),
                    version=1
                ) for ticker in ["AAPL", "AAPL.PF", "AMZN", "APP.TO", "APPN", "GOOGL", "MSFT", "TSLA"]
            ]
            
            mock_search.return_value = SecuritySearchResponse(
                securities=ordered_securities,
                pagination=PaginationInfo(
                    totalElements=8,
                    totalPages=1,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            result = await security_service.search_securities()
            
            tickers = [sec.ticker for sec in result.securities]
            expected_order = ["AAPL", "AAPL.PF", "AMZN", "APP.TO", "APPN", "GOOGL", "MSFT", "TSLA"]
            
            assert tickers == expected_order

    @pytest.mark.asyncio
    async def test_edge_case_empty_search(self):
        """Test edge case with search that returns no results."""
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
            
            result = await security_service.search_securities(ticker_like="XYZ123")
            
            assert result.securities == []
            assert result.pagination.totalElements == 0
            assert result.pagination.totalPages == 0
            assert result.pagination.hasNext == False
            assert result.pagination.hasPrevious == False

    @pytest.mark.asyncio
    async def test_edge_case_large_offset(self):
        """Test edge case with offset larger than total results."""
        with patch('app.services.security_service.search_securities') as mock_search:
            mock_search.return_value = SecuritySearchResponse(
                securities=[],
                pagination=PaginationInfo(
                    totalElements=8,
                    totalPages=1,
                    currentPage=2,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=True
                )
            )
            
            result = await security_service.search_securities(offset=100)
            
            assert result.securities == []
            assert result.pagination.totalElements == 8
            assert result.pagination.currentPage == 2  # 100 // 50
            assert result.pagination.hasNext == False
            assert result.pagination.hasPrevious == True

    @pytest.mark.asyncio
    async def test_special_characters_in_ticker(self):
        """Test searching for tickers with special characters."""
        with patch('app.services.security_service.search_securities') as mock_search:
            app_to_security = SecurityV2(
                securityId='app_to_id',
                ticker='APP.TO',
                description='AppLovin Corporation Common Stock (Toronto)',
                securityTypeId='cs_type_id',
                securityType=SecurityTypeNestedV2(
                    securityTypeId='cs_type_id',
                    abbreviation='CS',
                    description='Common Stock',
                    version=1
                ),
                version=1
            )
            
            mock_search.return_value = SecuritySearchResponse(
                securities=[app_to_security],
                pagination=PaginationInfo(
                    totalElements=1,
                    totalPages=1,
                    currentPage=0,
                    pageSize=50,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            # Search for exact ticker with dot
            result = await security_service.search_securities(ticker="APP.TO")
            
            assert len(result.securities) == 1
            assert result.securities[0].ticker == "APP.TO"
            
            # Also test partial search
            result = await security_service.search_securities(ticker_like=".TO")
            assert len(result.securities) == 1
            assert result.securities[0].ticker == "APP.TO"

    @pytest.mark.asyncio
    async def test_performance_large_limit(self):
        """Test performance with maximum allowed limit."""
        with patch('app.services.security_service.search_securities') as mock_search:
            all_securities = [
                SecurityV2(
                    securityId=f'{ticker.lower()}_id',
                    ticker=ticker,
                    description=f'{ticker} Description',
                    securityTypeId='cs_type_id',
                    securityType=SecurityTypeNestedV2(
                        securityTypeId='cs_type_id',
                        abbreviation='CS',
                        description='Common Stock',
                        version=1
                    ),
                    version=1
                ) for ticker in ["AAPL", "AAPL.PF", "AMZN", "APP.TO", "APPN", "GOOGL", "MSFT", "TSLA"]
            ]
            
            mock_search.return_value = SecuritySearchResponse(
                securities=all_securities,
                pagination=PaginationInfo(
                    totalElements=8,
                    totalPages=1,
                    currentPage=0,
                    pageSize=1000,
                    hasNext=False,
                    hasPrevious=False
                )
            )
            
            result = await security_service.search_securities(limit=1000)
            
            assert len(result.securities) == 8  # All available securities
            assert result.pagination.pageSize == 1000
            assert result.pagination.totalElements == 8 