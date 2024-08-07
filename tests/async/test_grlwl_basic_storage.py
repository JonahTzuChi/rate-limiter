import pytest
from pygrl import BasicStorage, GeneralRateLimiter_with_Lock as grl
import time
from typing import Any


STORAGE = BasicStorage()


@pytest.fixture(autouse=True)
def setup():
    STORAGE.clear()
    print("\n======= BEG =======")
    yield
    STORAGE.clear()
    print("\n======= END =======")


@pytest.mark.asyncio
@pytest.mark.parametrize("max_requests,time_window", [(3, 3), (10, 5), (5, 4)])
async def test_grlwl_bs_check_limit_w_same_key(max_requests: int, time_window: int):
    # Parameter
    key = "key"
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)
    t1 = time.time()
    for _ in range(max_requests):
        # The rate limiter should allow access up to `max_requests` times within the `time_window`.
        assert await rate_limiter.check_limit(key)
    # Expect to return False from `max_requests` + 1 onward.
    assert not await rate_limiter.check_limit(key)
    # Runtime check
    diff = time.time() - t1
    if diff > time_window:
        raise RuntimeError("Previous steps took longer than the time window")
    # Pause the execution until the `time_window`
    time.sleep(time_window - diff)
    # Expect the rate limit to be lifted
    assert await rate_limiter.check_limit(key)

@pytest.mark.asyncio
@pytest.mark.parametrize("max_requests,time_window", [(3, 3), (10, 5), (5, 4)])
async def test_grlwl_bs__call__w_same_key(max_requests: int, time_window: int):
    # Parameter
    key = "key"
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)
    t1 = time.time()
    for _ in range(max_requests):
        # The rate limiter should allow access up to `max_requests` times within the `time_window`.
        assert await rate_limiter(key)
    # Expect to return False from `max_requests` + 1 onward.
    assert not await rate_limiter(key)
    # Runtime check
    diff = time.time() - t1
    if diff > time_window:
        raise RuntimeError("Previous steps took longer than the time window")
    # Pause the execution until the `time_window`
    time.sleep(time_window - diff)
    # Expect the rate limit to be lifted
    assert await rate_limiter(key)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "max_requests,time_window,number_of_key", [(5, 5, 3), (10, 5, 10), (3, 3, 7)]
)
async def test_grlwl_bs_check_limit_w_different_key(
    max_requests: int, time_window: int, number_of_key: int
):
    # Variable
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)

    start = time.time()
    # Load the rate limiter up to it's threshold
    for _ in range(max_requests):
        # Arrange in such a way to ensure all keys are registered almost the same time
        for key_index in range(number_of_key):
            assert await rate_limiter.check_limit(key_index)
    # variable `buffer` & `delay` exists for the sake of simulation
    buffer = 0.05  # Warning: Does not scale with the `number_of_key` and `time_window`
    delay = 0.1  # Warning: Does not scale with the `number_of_key` and `time_window`
    # Expect rate limits continue to hold until the time_window is exceeded
    while time.time() - start < time_window - buffer:
        # Assumpt for-loop below require less than `buffer` to finish,
        # Otherwise, rate limiting of the last few keys might be lifted, thus fail the test
        for key_index in range(number_of_key):
            assert not await rate_limiter.check_limit(key_index)
        time.sleep(delay)  # Force a short sleep to reduce resource allocation
    time.sleep(buffer)  # Ensure the time_window is reached
    # Expect rate limits to be lifted
    for key_index in range(number_of_key):
        assert await rate_limiter.check_limit(key_index)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "max_requests,time_window,number_of_key", [(5, 5, 3), (10, 5, 10), (3, 3, 7)]
)
async def test_grlwl_bs__call__w_different_key(
    max_requests: int, time_window: int, number_of_key: int
):
    # Variable
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)

    start = time.time()
    # Load the rate limiter up to it's threshold
    for _ in range(max_requests):
        # Arrange in such a way to ensure all keys are registered almost the same time
        for key_index in range(number_of_key):
            assert await rate_limiter(key_index)
    # variable `buffer` & `delay` exists for the sake of simulation
    buffer = 0.05  # Warning: Does not scale with the `number_of_key` and `time_window`
    delay = 0.1  # Warning: Does not scale with the `number_of_key` and `time_window`
    # Expect rate limits continue to hold until the time_window is exceeded
    while time.time() - start < time_window - buffer:
        # Assumpt for-loop below require less than `buffer` to finish,
        # Otherwise, rate limiting of the last few keys might be lifted, thus fail the test
        for key_index in range(number_of_key):
            assert not await rate_limiter(key_index)
        time.sleep(delay)  # Force a short sleep to reduce resource allocation
    time.sleep(buffer)  # Ensure the time_window is reached
    # Expect rate limits to be lifted
    for key_index in range(number_of_key):
        assert await rate_limiter(key_index)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "max_requests,time_window,keys,key,expected",
    [
        (5, 10, [1, 1, 2, 1, 1, 2, 1], 1, False),
        (5, 10, [1, 1, 2, 1, 1, 2, 1], 2, True),
        (3, 5, ["a", "b", "a", "b", "c", "a", "b"], "a", False),
        (3, 5, ["a", "b", "a", "b", "c", "a", "b"], "c", True),
        (4, 15, ["a", "b", "a", "b", "c", "a", "b", "a", "c"], "a", False),
        (4, 15, ["a", "b", "a", "b", "c", "a", "b", "a", "c"], "b", True),
    ],
)
async def test_grlwl_bs_check_limit_w_different_key_sequence(
    max_requests: int, time_window: int, keys: list, key: Any, expected: bool
):
    # Variable
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)

    t1 = time.time()
    # Pre-load the rate limiter with keys
    for k in keys:
        assert await rate_limiter.check_limit(k)
    # Test
    assert await rate_limiter.check_limit(key) is expected
    # Runtime check
    diff = time.time() - t1
    if diff > time_window:
        raise RuntimeError("Previous steps took longer than the time window")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "max_requests,time_window,keys,key,expected",
    [
        (5, 10, [1, 1, 2, 1, 1, 2, 1], 1, False),
        (5, 10, [1, 1, 2, 1, 1, 2, 1], 2, True),
        (3, 5, ["a", "b", "a", "b", "c", "a", "b"], "a", False),
        (3, 5, ["a", "b", "a", "b", "c", "a", "b"], "c", True),
        (4, 15, ["a", "b", "a", "b", "c", "a", "b", "a", "c"], "a", False),
        (4, 15, ["a", "b", "a", "b", "c", "a", "b", "a", "c"], "b", True),
    ],
)
async def test_grlwl_bs__call__w_different_key_sequence(
    max_requests: int, time_window: int, keys: list, key: Any, expected: bool
):
    # Variable
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)

    t1 = time.time()
    # Pre-load the rate limiter with keys
    for k in keys:
        assert await rate_limiter(k)
    # Test
    assert await rate_limiter(key) is expected
    # Runtime check
    diff = time.time() - t1
    if diff > time_window:
        raise RuntimeError("Previous steps took longer than the time window")


@pytest.mark.asyncio
@pytest.mark.parametrize("max_requests,time_window", [(3, 3), (4, 3), (10, 4)])
async def test_grlwl_bs_check_limit_reset(max_requests: int, time_window: int):
    # Parameter
    key = "key"
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)
    t1 = time.time()
    for _ in range(max_requests):
        # The rate limiter should allow access up to `max_requests` times within the `time_window`.
        assert await rate_limiter.check_limit(key)
    
    # Expect to return False from `max_requests` + 1 onward.
    assert not await rate_limiter.check_limit(key)
    
    # Runtime check
    diff = time.time() - t1
    if diff > time_window:
        raise RuntimeError("Previous steps took longer than the time window")
    
    # Reset the rate limiter
    await rate_limiter.reset()
    
    # Expect the rate limit to be lifted
    assert await rate_limiter.check_limit(key)


@pytest.mark.asyncio
@pytest.mark.parametrize("max_requests,time_window", [(3, 3), (4, 3), (10, 4)])
async def test_grlwl_bs__call__reset(max_requests: int, time_window: int):
    # Parameter
    key = "key"
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)
    t1 = time.time()
    for _ in range(max_requests):
        # The rate limiter should allow access up to `max_requests` times within the `time_window`.
        assert await rate_limiter(key)
    
    # Expect to return False from `max_requests` + 1 onward.
    assert not await rate_limiter(key)
    
    # Runtime check
    diff = time.time() - t1
    if diff > time_window:
        raise RuntimeError("Previous steps took longer than the time window")
    
    # Reset the rate limiter
    await rate_limiter.reset()
    
    # Expect the rate limit to be lifted
    assert await rate_limiter(key)


@pytest.mark.asyncio
@pytest.mark.parametrize("max_requests,time_window", [(3, 3), (4, 3), (10, 4)])
async def test_grlwl_check_limit_info(max_requests: int, time_window: int):
    # Parameter
    key = "key"
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)
    for _ in range(max_requests):
        await rate_limiter.check_limit(key)

    info: dict = await rate_limiter.info()
    keys: list = info["keys"]
    values: list = info["values"]
    assert len(keys) == len(values)
    for value in values:
        assert value["num_requests"] == max_requests


@pytest.mark.asyncio
@pytest.mark.parametrize("max_requests,time_window", [(3, 3), (4, 3), (10, 4)])
async def test_grlwl__call__info(max_requests: int, time_window: int):
    # Parameter
    key = "key"
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)
    for _ in range(max_requests):
        await rate_limiter(key)

    info: dict = await rate_limiter.info()
    keys: list = info["keys"]
    values: list = info["values"]
    assert len(keys) == len(values)
    for value in values:
        assert value["num_requests"] == max_requests


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "max_requests,time_window,sequence,expected",
    [
        (3, 3, [1, 1, 2, 2, 1, 3, 1, 2, 3], {"1": 4, "2": 3, "3": 2}),
        (
            4,
            5,
            ["a", "a", "b", "c", "d", "a", "b", "c", "e", "e"],
            {"a": 3, "b": 2, "c": 2, "d": 1, "e": 2},
        ),
    ],
)
async def test_grlwl_check_limit_sequence_info(
    max_requests: int, time_window: int, sequence: list, expected: dict
):
    # Parameter
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)
    for value in sequence:
        await rate_limiter.check_limit(value)

    info: dict = await rate_limiter.info()
    keys: list = info["keys"]
    values: list = info["values"]
    assert len(keys) == len(values)

    for k, v in zip(keys, values):
        assert v["num_requests"] == expected.get(k)
        

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "max_requests,time_window,sequence,expected",
    [
        (3, 3, [1, 1, 2, 2, 1, 3, 1, 2, 3], {"1": 4, "2": 3, "3": 2}),
        (
            4,
            5,
            ["a", "a", "b", "c", "d", "a", "b", "c", "e", "e"],
            {"a": 3, "b": 2, "c": 2, "d": 1, "e": 2},
        ),
    ],
)
async def test_grlwl__call__sequence_info(
    max_requests: int, time_window: int, sequence: list, expected: dict
):
    # Parameter
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)
    for value in sequence:
        await rate_limiter(value)

    info: dict = await rate_limiter.info()
    keys: list = info["keys"]
    values: list = info["values"]
    assert len(keys) == len(values)

    for k, v in zip(keys, values):
        assert v["num_requests"] == expected.get(k)
        

@pytest.mark.asyncio
@pytest.mark.parametrize("max_requests,time_window", [(3, 3), (4, 5)])
async def test_grlwl_info(max_requests: int, time_window: int):
    # Parameter
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)
    
    # Expect the initial state to be empty
    info: dict = await rate_limiter.info()
    keys: list = info["keys"]
    values: list = info["values"]
    assert len(keys) == len(values)
    assert len(keys) == 0
    
    # Load the rate limiter up to it's threshold
    for _ in range(max_requests):
        await rate_limiter.check_limit("key")
    
    # Expect the state to be full
    post_info: dict = await rate_limiter.info()
    post_keys: list = post_info["keys"]
    post_values: list = post_info["values"]
    assert len(post_keys) == len(post_values)
    assert len(post_keys) == 1
    assert post_values[0]['num_requests'] == max_requests
    

@pytest.mark.asyncio
@pytest.mark.parametrize("max_requests,time_window", [(3, 3), (4, 5)])
async def test_grlwl_info_after_reset(max_requests: int, time_window: int):
    # Parameter
    rate_limiter = grl(STORAGE, max_requests=max_requests, time_window=time_window)
    
    start = time.time()
    # Load the rate limiter up to it's threshold
    for _ in range(max_requests):
        await rate_limiter.check_limit("key")
    
    # Expect the state to be full
    info: dict = await rate_limiter.info()
    keys: list = info["keys"]
    values: list = info["values"]
    assert len(keys) == len(values)
    assert len(keys) == 1
    assert values[0]['num_requests'] == max_requests
    
    # Reset the rate limiter
    await rate_limiter.reset()
    
    # Expect the state to be empty after reset
    post_info: dict = await rate_limiter.info()
    post_keys: list = post_info["keys"]
    post_values: list = post_info["values"]
    assert len(post_keys) == len(post_values)
    assert len(post_keys) == 0

    # Runtime check
    diff = time.time() - start
    if diff > time_window:
        raise RuntimeError("Previous steps took longer than the time window")
