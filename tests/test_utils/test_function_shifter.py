import pytest
import time
import asyncio

from agently.utils import FunctionShifter


# Test functions
def sync_func(x: int, y: int) -> int:
    """Synchronous function"""
    time.sleep(0.1)  # Simulate time-consuming operation
    return x + y


async def async_func(x: int, y: int) -> int:
    """Asynchronous function"""
    await asyncio.sleep(0.1)  # Simulate asynchronous operation
    return x * y


@pytest.mark.asyncio
async def test_async():
    """Test in asynchronous context"""
    print("=== Async context test ===")

    # Test ensure_awaitable
    awaitable_sync = FunctionShifter.ensure_awaitable(sync_func)
    result1 = await awaitable_sync(2, 3)
    print(f"sync_func -> awaitable: {result1}")

    awaitable_async = FunctionShifter.ensure_awaitable(async_func)
    result2 = await awaitable_async(2, 3)
    print(f"async_func -> awaitable: {result2}")

    # Test hybrid_func
    hybrid_sync = FunctionShifter.hybrid_func(sync_func)
    result3 = await hybrid_sync(4, 5)  # type: ignore
    print(f"hybrid sync in async context: {result3}")

    hybrid_async = FunctionShifter.hybrid_func(async_func)
    result4 = await hybrid_async(4, 5)  # type: ignore
    print(f"hybrid async in async context: {result4}")


def test_sync():
    """Test in synchronous context"""
    print("\n=== Sync context test ===")

    # Test ensure_sync
    sync_async = FunctionShifter.ensure_sync(async_func)
    result1 = sync_async(2, 3)
    print(f"async_func -> sync: {result1}")

    sync_sync = FunctionShifter.ensure_sync(sync_func)
    result2 = sync_sync(2, 3)
    print(f"sync_func -> sync: {result2}")

    # Test hybrid_func
    hybrid_sync = FunctionShifter.hybrid_func(sync_func)
    result3 = hybrid_sync(4, 5)
    print(f"hybrid sync in sync context: {result3}")

    hybrid_async = FunctionShifter.hybrid_func(async_func)
    result4 = hybrid_async(4, 5)
    print(f"hybrid async in sync context: {result4}")
