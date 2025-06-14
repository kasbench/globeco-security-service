import pytest
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.services import security_service
from app.models.security import Security
from app.models.security_type import SecurityType

class TestV2Performance:
    """Performance tests for v2 securities search functionality."""

    @pytest.fixture
    async def large_dataset(self, sample_security_types):
        """Create a large dataset for performance testing."""
        cs_type = next(st for st in sample_security_types if st.abbreviation == "CS")
        
        # Create 1000 securities for performance testing
        securities = []
        for i in range(1000):
            ticker = f"TEST{i:04d}"
            description = f"Test Security {i:04d} Corporation"
            security = Security(
                ticker=ticker,
                description=description,
                security_type_id=cs_type.id,
                version=1
            )
            securities.append(security)
        
        # Batch insert for better performance
        await Security.insert_many(securities)
        return securities

    @pytest.mark.asyncio
    async def test_search_all_performance(self, large_dataset):
        """Test performance of searching all securities."""
        start_time = time.time()
        
        result = await security_service.search_securities()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within 2 seconds for 1000+ records
        assert execution_time < 2.0, f"Search took {execution_time:.2f} seconds, expected < 2.0"
        
        # Should return all securities plus sample data
        assert result.pagination.totalElements >= 1000
        assert len(result.securities) >= 50  # Default page size

    @pytest.mark.asyncio
    async def test_exact_search_performance(self, large_dataset):
        """Test performance of exact ticker search."""
        start_time = time.time()
        
        result = await security_service.search_securities(ticker="TEST0500")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Exact search should be very fast (< 0.1 seconds)
        assert execution_time < 0.1, f"Exact search took {execution_time:.2f} seconds, expected < 0.1"
        
        # Should find exactly one result
        assert len(result.securities) == 1
        assert result.securities[0].ticker == "TEST0500"

    @pytest.mark.asyncio
    async def test_partial_search_performance(self, large_dataset):
        """Test performance of partial ticker search."""
        start_time = time.time()
        
        # Search for "TEST05" which should match TEST0500-TEST0599
        result = await security_service.search_securities(ticker_like="TEST05")
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Partial search should complete within 1 second
        assert execution_time < 1.0, f"Partial search took {execution_time:.2f} seconds, expected < 1.0"
        
        # Should find multiple results (TEST0500-TEST0599)
        assert len(result.securities) >= 50  # At least 50 matches (limited by page size)
        assert result.pagination.totalElements >= 100  # Should be 100 total matches

    @pytest.mark.asyncio
    async def test_pagination_performance(self, large_dataset):
        """Test performance of paginated results."""
        start_time = time.time()
        
        # Get multiple pages to test pagination performance
        page1 = await security_service.search_securities(limit=100, offset=0)
        page2 = await security_service.search_securities(limit=100, offset=100)
        page3 = await security_service.search_securities(limit=100, offset=200)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # All three page requests should complete within 1 second
        assert execution_time < 1.0, f"Pagination took {execution_time:.2f} seconds, expected < 1.0"
        
        # Each page should have 100 results
        assert len(page1.securities) == 100
        assert len(page2.securities) == 100
        assert len(page3.securities) == 100
        
        # No overlap between pages
        page1_tickers = {sec.ticker for sec in page1.securities}
        page2_tickers = {sec.ticker for sec in page2.securities}
        page3_tickers = {sec.ticker for sec in page3.securities}
        
        assert len(page1_tickers & page2_tickers) == 0
        assert len(page2_tickers & page3_tickers) == 0
        assert len(page1_tickers & page3_tickers) == 0

    @pytest.mark.asyncio
    async def test_concurrent_search_performance(self, large_dataset):
        """Test performance under concurrent load."""
        async def search_task(search_term):
            """Individual search task."""
            return await security_service.search_securities(ticker_like=search_term)
        
        # Create 10 concurrent search tasks
        search_terms = [f"TEST{i:02d}" for i in range(10)]
        
        start_time = time.time()
        
        # Execute all searches concurrently
        tasks = [search_task(term) for term in search_terms]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # All 10 concurrent searches should complete within 3 seconds
        assert execution_time < 3.0, f"Concurrent searches took {execution_time:.2f} seconds, expected < 3.0"
        
        # All searches should return results
        assert len(results) == 10
        for result in results:
            assert result.pagination.totalElements > 0

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, large_dataset):
        """Test memory efficiency with large result sets."""
        # Search with large page size
        result = await security_service.search_securities(limit=1000)
        
        # Should handle large page sizes without issues
        assert len(result.securities) <= 1000
        assert result.pagination.totalElements >= 1000
        
        # Verify all securities have required fields populated
        for security in result.securities:
            assert security.securityId is not None
            assert security.ticker is not None
            assert security.description is not None
            assert security.securityType is not None

    @pytest.mark.asyncio
    async def test_index_effectiveness(self, large_dataset):
        """Test that database indexes are effective for search performance."""
        # Test exact search (should use ticker index)
        start_time = time.time()
        exact_result = await security_service.search_securities(ticker="TEST0001")
        exact_time = time.time() - start_time
        
        # Test partial search (should use text index or regex)
        start_time = time.time()
        partial_result = await security_service.search_securities(ticker_like="TEST")
        partial_time = time.time() - start_time
        
        # Exact search should be faster than partial search
        assert exact_time < partial_time, "Exact search should be faster than partial search"
        
        # Both should be reasonably fast
        assert exact_time < 0.1, f"Exact search too slow: {exact_time:.3f}s"
        assert partial_time < 1.0, f"Partial search too slow: {partial_time:.3f}s"

    @pytest.mark.asyncio
    async def test_search_result_consistency(self, large_dataset):
        """Test that search results are consistent across multiple calls."""
        # Perform the same search multiple times
        search_term = "TEST01"
        
        results = []
        for _ in range(5):
            result = await security_service.search_securities(ticker_like=search_term)
            results.append(result)
        
        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.pagination.totalElements == first_result.pagination.totalElements
            assert len(result.securities) == len(first_result.securities)
            
            # Check that tickers are in the same order
            first_tickers = [sec.ticker for sec in first_result.securities]
            result_tickers = [sec.ticker for sec in result.securities]
            assert first_tickers == result_tickers

    @pytest.mark.asyncio
    async def test_edge_case_performance(self, large_dataset):
        """Test performance with edge cases."""
        # Test search with no results
        start_time = time.time()
        no_results = await security_service.search_securities(ticker_like="NONEXISTENT")
        no_results_time = time.time() - start_time
        
        # Test search with single character (many results)
        start_time = time.time()
        many_results = await security_service.search_securities(ticker_like="T")
        many_results_time = time.time() - start_time
        
        # Test large offset
        start_time = time.time()
        large_offset = await security_service.search_securities(offset=900, limit=50)
        large_offset_time = time.time() - start_time
        
        # All edge cases should complete quickly
        assert no_results_time < 0.5, f"No results search too slow: {no_results_time:.3f}s"
        assert many_results_time < 1.0, f"Many results search too slow: {many_results_time:.3f}s"
        assert large_offset_time < 1.0, f"Large offset search too slow: {large_offset_time:.3f}s"
        
        # Verify results
        assert no_results.pagination.totalElements == 0
        assert many_results.pagination.totalElements > 0
        assert len(large_offset.securities) > 0  # Should still have results

    @pytest.mark.asyncio
    async def test_database_connection_efficiency(self, large_dataset):
        """Test that database connections are used efficiently."""
        # Perform multiple searches in sequence
        start_time = time.time()
        
        for i in range(20):
            await security_service.search_securities(ticker=f"TEST{i:04d}")
        
        end_time = time.time()
        total_time = end_time - start_time
        average_time = total_time / 20
        
        # Average time per search should be reasonable
        assert average_time < 0.1, f"Average search time too high: {average_time:.3f}s"
        assert total_time < 2.0, f"Total time for 20 searches too high: {total_time:.2f}s" 