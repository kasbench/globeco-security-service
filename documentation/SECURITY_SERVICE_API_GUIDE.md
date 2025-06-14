# GlobeCo Security Service API Integration Guide for Order Service

## Overview

This guide provides comprehensive documentation for integrating the GlobeCo Security Service v2 API with the Order Service. The v2 API enables the Order Service to resolve human-readable ticker symbols to security IDs for database filtering operations.

**Author**: Noah Krieger  
**Service**: GlobeCo Security Service  
**Target Integration**: Order Service LLM  
**API Version**: v2  

## Quick Start

### Base URL
```
http://globeco-security-service:8000/api/v2
```

### Primary Endpoint
```
GET /api/v2/securities
```

## Integration Use Cases

### 1. Ticker to Security ID Resolution

**Use Case**: Order Service needs to filter orders by `security.ticker=AAPL` but requires the `securityId` for database queries.

**Solution**: Use exact ticker search to resolve ticker to security ID.

```python
async def resolve_ticker_to_security_id(ticker: str) -> Optional[str]:
    """
    Resolve a ticker symbol to its corresponding security ID.
    
    Args:
        ticker: The ticker symbol (e.g., "AAPL")
        
    Returns:
        Security ID if found, None otherwise
    """
    try:
        response = await http_client.get(
            f"http://globeco-security-service:8000/api/v2/securities?ticker={ticker}"
        )
        
        if response.status_code == 200:
            data = response.json()
            if data["securities"]:
                return data["securities"][0]["securityId"]
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to resolve ticker {ticker}: {e}")
        return None
```

**Example Request**:
```bash
GET /api/v2/securities?ticker=AAPL
```

**Example Response**:
```json
{
  "securities": [
    {
      "securityId": "60c72b2f9b1e8b3f8c8b4567",
      "ticker": "AAPL",
      "description": "Apple Inc. Common Stock",
      "securityTypeId": "60c72b2f9b1e8b3f8c8b4568",
      "version": 1,
      "securityType": {
        "securityTypeId": "60c72b2f9b1e8b3f8c8b4568",
        "abbreviation": "CS",
        "description": "Common Stock",
        "version": 1
      }
    }
  ],
  "pagination": {
    "totalElements": 1,
    "totalPages": 1,
    "currentPage": 0,
    "pageSize": 50,
    "hasNext": false,
    "hasPrevious": false
  }
}
```

### 2. Bulk Ticker Resolution

**Use Case**: Order Service needs to resolve multiple tickers efficiently.

```python
async def resolve_multiple_tickers(tickers: List[str]) -> Dict[str, Optional[str]]:
    """
    Resolve multiple tickers to their security IDs.
    
    Args:
        tickers: List of ticker symbols
        
    Returns:
        Dictionary mapping ticker to security ID (or None if not found)
    """
    results = {}
    
    # Use asyncio.gather for concurrent requests
    tasks = [resolve_ticker_to_security_id(ticker) for ticker in tickers]
    security_ids = await asyncio.gather(*tasks, return_exceptions=True)
    
    for ticker, security_id in zip(tickers, security_ids):
        if isinstance(security_id, Exception):
            results[ticker] = None
        else:
            results[ticker] = security_id
    
    return results
```

### 3. Fuzzy Ticker Search

**Use Case**: Order Service receives partial or fuzzy ticker input and needs to find matching securities.

```python
async def search_tickers_like(partial_ticker: str, limit: int = 10) -> List[Dict]:
    """
    Search for securities with tickers containing the partial string.
    
    Args:
        partial_ticker: Partial ticker string (e.g., "APP")
        limit: Maximum number of results
        
    Returns:
        List of matching securities
    """
    try:
        response = await http_client.get(
            f"http://globeco-security-service:8000/api/v2/securities"
            f"?ticker_like={partial_ticker}&limit={limit}"
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["securities"]
        
        return []
        
    except Exception as e:
        logger.error(f"Failed to search tickers like {partial_ticker}: {e}")
        return []
```

**Example Request**:
```bash
GET /api/v2/securities?ticker_like=APP&limit=5
```

## API Parameters

### Query Parameters

| Parameter | Type | Required | Description | Validation |
|-----------|------|----------|-------------|------------|
| `ticker` | string | No | Exact ticker match (case-insensitive) | 1-50 chars, alphanumeric + dots/hyphens |
| `ticker_like` | string | No | Partial ticker match (case-insensitive) | 1-50 chars, alphanumeric + dots/hyphens |
| `limit` | integer | No | Max results (default: 50) | 1-1000 |
| `offset` | integer | No | Results to skip (default: 0) | ≥ 0 |

### Parameter Rules

1. **Mutual Exclusivity**: Only one of `ticker` or `ticker_like` can be provided
2. **Ticker Format**: Must match pattern `^[A-Za-z0-9.-]{1,50}$`
3. **Default Behavior**: No search params returns all securities with pagination

## Response Schema

### Success Response (HTTP 200)

```json
{
  "securities": [
    {
      "securityId": "string",
      "ticker": "string", 
      "description": "string",
      "securityTypeId": "string",
      "version": integer,
      "securityType": {
        "securityTypeId": "string",
        "abbreviation": "string",
        "description": "string", 
        "version": integer
      }
    }
  ],
  "pagination": {
    "totalElements": integer,
    "totalPages": integer,
    "currentPage": integer,
    "pageSize": integer,
    "hasNext": boolean,
    "hasPrevious": boolean
  }
}
```

### Error Responses

#### HTTP 400 - Bad Request
```json
{
  "detail": "Only one of 'ticker' or 'ticker_like' parameters can be provided"
}
```

#### HTTP 422 - Validation Error
```json
{
  "detail": [
    {
      "loc": ["query", "ticker"],
      "msg": "String should match pattern '^[A-Za-z0-9.-]{1,50}$'",
      "type": "string_pattern_mismatch"
    }
  ]
}
```

## Error Handling Best Practices

### 1. Robust Error Handling

```python
async def safe_ticker_resolution(ticker: str) -> Optional[str]:
    """
    Safely resolve ticker with comprehensive error handling.
    """
    try:
        response = await http_client.get(
            f"http://globeco-security-service:8000/api/v2/securities?ticker={ticker}",
            timeout=5.0  # 5 second timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            if data["securities"]:
                return data["securities"][0]["securityId"]
            else:
                logger.warning(f"Ticker {ticker} not found")
                return None
                
        elif response.status_code == 400:
            logger.error(f"Invalid ticker format: {ticker}")
            return None
            
        elif response.status_code == 422:
            logger.error(f"Validation error for ticker: {ticker}")
            return None
            
        else:
            logger.error(f"Unexpected response {response.status_code} for ticker {ticker}")
            return None
            
    except asyncio.TimeoutError:
        logger.error(f"Timeout resolving ticker {ticker}")
        return None
        
    except Exception as e:
        logger.error(f"Error resolving ticker {ticker}: {e}")
        return None
```

### 2. Retry Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def resolve_ticker_with_retry(ticker: str) -> Optional[str]:
    """
    Resolve ticker with exponential backoff retry.
    """
    return await resolve_ticker_to_security_id(ticker)
```

## Performance Considerations

### 1. Response Time Expectations

- **Exact ticker lookup**: < 200ms
- **Partial ticker search**: < 500ms
- **Paginated results**: < 400ms per page

### 2. Caching Strategy

```python
from functools import lru_cache
import time

class TickerCache:
    def __init__(self, ttl_seconds: int = 300):  # 5 minute TTL
        self.cache = {}
        self.ttl = ttl_seconds
    
    async def get_security_id(self, ticker: str) -> Optional[str]:
        """
        Get security ID with caching.
        """
        now = time.time()
        
        # Check cache
        if ticker in self.cache:
            cached_time, security_id = self.cache[ticker]
            if now - cached_time < self.ttl:
                return security_id
        
        # Fetch from API
        security_id = await resolve_ticker_to_security_id(ticker)
        
        # Cache result
        self.cache[ticker] = (now, security_id)
        
        return security_id

# Global cache instance
ticker_cache = TickerCache()
```

### 3. Connection Pooling

```python
import aiohttp

class SecurityServiceClient:
    def __init__(self):
        self.base_url = "http://globeco-security-service:8000/api/v2"
        self.session = None
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=10, connect=5)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def resolve_ticker(self, ticker: str) -> Optional[str]:
        """
        Resolve ticker using connection pool.
        """
        async with self.session.get(
            f"{self.base_url}/securities",
            params={"ticker": ticker}
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data["securities"]:
                    return data["securities"][0]["securityId"]
            return None

# Usage
async with SecurityServiceClient() as client:
    security_id = await client.resolve_ticker("AAPL")
```

## Integration Patterns

### 1. Order Filtering Integration

```python
async def filter_orders_by_ticker(ticker: str, other_filters: Dict) -> List[Order]:
    """
    Filter orders by ticker symbol.
    """
    # Resolve ticker to security ID
    security_id = await resolve_ticker_to_security_id(ticker)
    
    if not security_id:
        raise ValueError(f"Ticker {ticker} not found")
    
    # Add security filter to database query
    filters = {**other_filters, "security_id": security_id}
    
    # Execute order query
    return await order_repository.find_orders(filters)
```

### 2. Order Validation

```python
async def validate_order_security(order_data: Dict) -> bool:
    """
    Validate that the security ticker in an order exists.
    """
    ticker = order_data.get("security_ticker")
    
    if not ticker:
        return True  # No ticker to validate
    
    security_id = await resolve_ticker_to_security_id(ticker)
    
    if security_id:
        # Enrich order data with security ID
        order_data["security_id"] = security_id
        return True
    
    return False
```

### 3. Autocomplete/Search Integration

```python
async def get_ticker_suggestions(partial_ticker: str) -> List[Dict]:
    """
    Get ticker suggestions for autocomplete.
    """
    if len(partial_ticker) < 2:
        return []
    
    securities = await search_tickers_like(partial_ticker, limit=10)
    
    return [
        {
            "ticker": security["ticker"],
            "description": security["description"],
            "securityId": security["securityId"]
        }
        for security in securities
    ]
```

## Testing Integration

### 1. Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_resolve_ticker_success():
    """Test successful ticker resolution."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "securities": [{"securityId": "test-id"}],
        "pagination": {}
    }
    
    with patch('http_client.get', return_value=mock_response):
        result = await resolve_ticker_to_security_id("AAPL")
        assert result == "test-id"

@pytest.mark.asyncio
async def test_resolve_ticker_not_found():
    """Test ticker not found scenario."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "securities": [],
        "pagination": {}
    }
    
    with patch('http_client.get', return_value=mock_response):
        result = await resolve_ticker_to_security_id("INVALID")
        assert result is None
```

### 2. Integration Tests

```python
@pytest.mark.asyncio
async def test_security_service_integration():
    """Test actual integration with security service."""
    # This requires the security service to be running
    async with SecurityServiceClient() as client:
        # Test known ticker
        security_id = await client.resolve_ticker("AAPL")
        assert security_id is not None
        
        # Test invalid ticker
        invalid_id = await client.resolve_ticker("INVALID_TICKER")
        assert invalid_id is None
```

## Monitoring and Observability

### 1. Metrics Collection

```python
import time
from prometheus_client import Counter, Histogram

# Metrics
ticker_resolution_requests = Counter(
    'ticker_resolution_requests_total',
    'Total ticker resolution requests',
    ['status']
)

ticker_resolution_duration = Histogram(
    'ticker_resolution_duration_seconds',
    'Ticker resolution request duration'
)

async def resolve_ticker_with_metrics(ticker: str) -> Optional[str]:
    """
    Resolve ticker with metrics collection.
    """
    start_time = time.time()
    
    try:
        result = await resolve_ticker_to_security_id(ticker)
        
        if result:
            ticker_resolution_requests.labels(status='success').inc()
        else:
            ticker_resolution_requests.labels(status='not_found').inc()
        
        return result
        
    except Exception as e:
        ticker_resolution_requests.labels(status='error').inc()
        raise
        
    finally:
        duration = time.time() - start_time
        ticker_resolution_duration.observe(duration)
```

### 2. Logging

```python
import logging
import json

logger = logging.getLogger(__name__)

async def resolve_ticker_with_logging(ticker: str) -> Optional[str]:
    """
    Resolve ticker with structured logging.
    """
    logger.info(
        "Resolving ticker",
        extra={
            "ticker": ticker,
            "service": "security-service",
            "operation": "ticker_resolution"
        }
    )
    
    try:
        result = await resolve_ticker_to_security_id(ticker)
        
        logger.info(
            "Ticker resolution completed",
            extra={
                "ticker": ticker,
                "security_id": result,
                "found": result is not None
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Ticker resolution failed",
            extra={
                "ticker": ticker,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )
        raise
```

## Security Considerations

### 1. Input Validation

```python
import re

def validate_ticker_format(ticker: str) -> bool:
    """
    Validate ticker format before API call.
    """
    if not ticker or len(ticker) > 50:
        return False
    
    return bool(re.match(r'^[A-Za-z0-9.-]+$', ticker))

async def safe_resolve_ticker(ticker: str) -> Optional[str]:
    """
    Safely resolve ticker with input validation.
    """
    if not validate_ticker_format(ticker):
        logger.warning(f"Invalid ticker format: {ticker}")
        return None
    
    return await resolve_ticker_to_security_id(ticker)
```

### 2. Rate Limiting

```python
import asyncio
from asyncio import Semaphore

class RateLimitedSecurityClient:
    def __init__(self, max_concurrent_requests: int = 10):
        self.semaphore = Semaphore(max_concurrent_requests)
    
    async def resolve_ticker(self, ticker: str) -> Optional[str]:
        """
        Resolve ticker with rate limiting.
        """
        async with self.semaphore:
            return await resolve_ticker_to_security_id(ticker)

# Global rate-limited client
security_client = RateLimitedSecurityClient()
```

## Troubleshooting Guide

### Common Issues

1. **Ticker Not Found**
   - Verify ticker format (alphanumeric + dots/hyphens only)
   - Check if ticker exists in the security database
   - Ensure case-insensitive search is working

2. **Timeout Errors**
   - Check network connectivity to security service
   - Verify security service health endpoints
   - Consider increasing timeout values

3. **Validation Errors**
   - Ensure ticker format matches `^[A-Za-z0-9.-]{1,50}$`
   - Check that only one of `ticker` or `ticker_like` is provided
   - Verify limit and offset parameter bounds

4. **Performance Issues**
   - Implement caching for frequently accessed tickers
   - Use connection pooling for multiple requests
   - Consider batch resolution for multiple tickers

### Health Check Integration

```python
async def check_security_service_health() -> bool:
    """
    Check if security service is healthy.
    """
    try:
        response = await http_client.get(
            "http://globeco-security-service:8000/health/readiness",
            timeout=5.0
        )
        return response.status_code == 200
    except:
        return False
```

## Summary

The GlobeCo Security Service v2 API provides robust ticker-to-security-ID resolution capabilities for the Order Service. Key integration points:

1. **Primary Use Case**: Resolve tickers to security IDs for order filtering
2. **Performance**: Sub-200ms response times for exact matches
3. **Error Handling**: Comprehensive validation and error responses
4. **Scalability**: Connection pooling and caching support
5. **Monitoring**: Built-in metrics and logging capabilities

For additional support or questions, refer to the main API documentation or contact the development team. 