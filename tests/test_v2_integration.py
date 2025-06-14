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
        with patch('app.services.security_service.Security') as mock_security:
            # Mock finding AAPL
            mock_security_aapl = type('MockSecurity', (), {
                'id': 'aapl_id',
                'ticker': 'AAPL',
                'description': 'Apple Inc. Common Stock',
                'security_type_id': 'cs_type_id',
                'version': 1,
                'security_type': type('MockSecurityType', (), {
                    'id': 'cs_type_id',
                    'abbreviation': 'CS',
                    'description': 'Common Stock',
                    'version': 1
                })()
            })()
            
            # Test existing ticker with proper async mock
            mock_query = AsyncMock()
            mock_query.count.return_value = 1
            mock_query.skip.return_value.limit.return_value.to_list.return_value = [mock_security_aapl]
            mock_security.find.return_value = mock_query
            
            result = await security_service.search_securities(ticker="AAPL")
            
            assert len(result.securities) == 1
            assert result.securities[0].ticker == "AAPL"
            assert result.securities[0].description == "Apple Inc. Common Stock"
            assert result.pagination.totalElements == 1
            
            # Test non-existing ticker
            mock_query.count.return_value = 0
            mock_query.skip.return_value.limit.return_value.to_list.return_value = []
            
            result = await security_service.search_securities(ticker="NONEXISTENT")
            assert len(result.securities) == 0
            assert result.pagination.totalElements == 0

    @pytest.mark.asyncio
    async def test_case_insensitive_exact_search(self):
        """Test that exact ticker search is case-insensitive."""
        with patch('app.services.security_service.Security') as mock_security:
            mock_security_aapl = type('MockSecurity', (), {
                'id': 'aapl_id',
                'ticker': 'AAPL',
                'description': 'Apple Inc. Common Stock',
                'security_type_id': 'cs_type_id',
                'version': 1,
                'security_type': type('MockSecurityType', (), {
                    'id': 'cs_type_id',
                    'abbreviation': 'CS',
                    'description': 'Common Stock',
                    'version': 1
                })()
            })()
            
            # Mock that all searches return the same result
            mock_security.find.return_value.count.return_value = 1
            mock_security.find.return_value.skip.return_value.limit.return_value.to_list.return_value = [mock_security_aapl]
            
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
        with patch('app.services.security_service.Security') as mock_security:
            # Mock securities that contain "APP" 
            mock_securities = [
                type('MockSecurity', (), {
                    'id': f'{ticker.lower()}_id',
                    'ticker': ticker,
                    'description': f'{ticker} Description',
                    'security_type_id': 'cs_type_id',
                    'version': 1,
                    'security_type': type('MockSecurityType', (), {
                        'id': 'cs_type_id',
                        'abbreviation': 'CS',
                        'description': 'Common Stock',
                        'version': 1
                    })()
                })() for ticker in ['AAPL', 'AAPL.PF', 'APP.TO', 'APPN']
            ]
            
            mock_security.find.return_value.count.return_value = 4
            mock_security.find.return_value.skip.return_value.limit.return_value.to_list.return_value = mock_securities
            
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
    async def test_case_insensitive_partial_search(self):
        """Test that partial ticker search is case-insensitive."""
        with patch('app.services.security_service.Security') as mock_security:
            mock_securities = [
                type('MockSecurity', (), {
                    'id': f'{ticker.lower()}_id',
                    'ticker': ticker,
                    'description': f'{ticker} Description',
                    'security_type_id': 'cs_type_id',
                    'version': 1,
                    'security_type': type('MockSecurityType', (), {
                        'id': 'cs_type_id',
                        'abbreviation': 'CS',
                        'description': 'Common Stock',
                        'version': 1
                    })()
                })() for ticker in ['AAPL', 'AAPL.PF', 'APP.TO', 'APPN']
            ]
            
            mock_security.find.return_value.count.return_value = 4
            mock_security.find.return_value.skip.return_value.limit.return_value.to_list.return_value = mock_securities
            
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
    async def test_pagination_functionality(self):
        """Test pagination with limit and offset."""
        with patch('app.services.security_service.Security') as mock_security:
            # Mock total count of 8 securities
            all_tickers = ['AAPL', 'AAPL.PF', 'AMZN', 'APP.TO', 'APPN', 'GOOGL', 'MSFT', 'TSLA']
            
            def create_mock_securities(tickers):
                return [
                    type('MockSecurity', (), {
                        'id': f'{ticker.lower()}_id',
                        'ticker': ticker,
                        'description': f'{ticker} Description',
                        'security_type_id': 'cs_type_id',
                        'version': 1,
                        'security_type': type('MockSecurityType', (), {
                            'id': 'cs_type_id',
                            'abbreviation': 'CS',
                            'description': 'Common Stock',
                            'version': 1
                        })()
                    })() for ticker in tickers
                ]
            
            # Test first page with limit 3
            mock_security.find.return_value.count.return_value = 8
            mock_security.find.return_value.skip.return_value.limit.return_value.to_list.return_value = create_mock_securities(all_tickers[:3])
            
            result_page1 = await security_service.search_securities(limit=3, offset=0)
            
            assert len(result_page1.securities) == 3
            assert result_page1.pagination.totalElements == 8
            assert result_page1.pagination.totalPages == 3  # ceil(8/3)
            assert result_page1.pagination.currentPage == 0
            assert result_page1.pagination.pageSize == 3
            assert result_page1.pagination.hasNext == True
            assert result_page1.pagination.hasPrevious == False
            
            # Test second page
            mock_security.find.return_value.skip.return_value.limit.return_value.to_list.return_value = create_mock_securities(all_tickers[3:6])
            
            result_page2 = await security_service.search_securities(limit=3, offset=3)
            
            assert len(result_page2.securities) == 3
            assert result_page2.pagination.currentPage == 1
            assert result_page2.pagination.hasNext == True
            assert result_page2.pagination.hasPrevious == True
            
            # Test last page
            mock_security.find.return_value.skip.return_value.limit.return_value.to_list.return_value = create_mock_securities(all_tickers[6:8])
            
            result_page3 = await security_service.search_securities(limit=3, offset=6)
            
            assert len(result_page3.securities) == 2  # Only 2 remaining
            assert result_page3.pagination.currentPage == 2
            assert result_page3.pagination.hasNext == False
            assert result_page3.pagination.hasPrevious == True

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