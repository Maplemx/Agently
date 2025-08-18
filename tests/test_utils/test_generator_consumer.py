import pytest

import asyncio
from agently.utils import GeneratorConsumer


@pytest.mark.asyncio
async def test_async_generator_multi_subscribe():
    async def async_gen():
        yield "a", 1
        yield "b", 2
        yield "c", 3

    consumer = GeneratorConsumer(async_gen())

    # First subscription
    gen1 = consumer.get_async_generator()
    collected1 = []
    async for value in gen1:
        collected1.append(value)

    # Second subscription should replay the same history
    gen2 = consumer.get_async_generator()
    collected2 = []
    async for value in gen2:
        collected2.append(value)

    assert collected1 == [("a", 1), ("b", 2), ("c", 3)]
    assert collected2 == collected1


@pytest.mark.asyncio
async def test_generator_consumer():
    async def original_gen():
        for i in range(0, 10):
            await asyncio.sleep(0.1)
            yield "number", i + 1

    consumer = GeneratorConsumer(original_gen())
    gen_1 = consumer.get_async_generator()
    gen_2 = consumer.get_async_generator()

    async def _consume(gen):
        n = 1
        async for value in gen:
            print(value)
            assert value == ("number", n)
            n += 1

    async def async_consume():
        task_1 = asyncio.create_task(_consume(gen_1))
        task_2 = asyncio.create_task(_consume(gen_2))
        await asyncio.gather(task_1, task_2)

    await async_consume()

    gen_3 = consumer.get_generator()
    n = 1
    for value in gen_3:
        print(value)
        assert value == ("number", n)
        n += 1


@pytest.mark.asyncio
async def test_sync_only():
    async def original_gen():
        for i in range(0, 10):
            await asyncio.sleep(0.1)
            yield "number", i + 1

    consumer = GeneratorConsumer(original_gen())
    gen = consumer.get_generator()
    n = 1
    for value in gen:
        print(value)
        assert value == ("number", n)
        n += 1


@pytest.mark.asyncio
async def test_exception_broadcast():
    async def faulty_gen():
        yield "start", 1
        raise ValueError("Something went wrong")

    consumer = GeneratorConsumer(faulty_gen())
    gen1 = consumer.get_async_generator()
    received = []

    with pytest.raises(ValueError, match="Something went wrong"):
        async for value in gen1:
            received.append(value)

    assert received == [("start", 1)]


@pytest.mark.asyncio
async def test_close_behavior():
    async def gen():
        yield "number", 42

    consumer = GeneratorConsumer(gen())
    async for _ in consumer.get_async_generator():
        pass

    await consumer.close()

    with pytest.raises(RuntimeError):
        async for _ in consumer.get_async_generator():
            pass

    with pytest.raises(RuntimeError):
        for _ in consumer.get_generator():
            pass


@pytest.mark.asyncio
async def test_get_result():
    async def original_gen():
        for i in range(5):
            yield "value", i

    consumer = GeneratorConsumer(original_gen())
    result = await consumer.get_result()
    assert result == [("value", i) for i in range(5)]


@pytest.mark.asyncio
async def test_generator_consumer_reuse_after_done():
    async def simple_gen():
        yield "x", 1
        yield "x", 2

    consumer = GeneratorConsumer(simple_gen())
    gen1 = consumer.get_async_generator()
    collected = []
    async for value in gen1:
        collected.append(value)

    # reuse after done
    gen2 = consumer.get_async_generator()
    replayed = []
    async for value in gen2:
        replayed.append(value)

    assert collected == [("x", 1), ("x", 2)]
    assert replayed == collected
