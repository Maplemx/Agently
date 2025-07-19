import pytest
from agently.utils import Storage, AsyncStorage
from sqlmodel import SQLModel, Field, Column, BLOB, TEXT, delete


def test_sqlite():
    storage = Storage(db_url="sqlite:///localstorage.db")

    class Test(SQLModel, table=True):
        __table_args__ = {"extend_existing": True}
        key: str = Field(primary_key=True)
        value: str | None = Field(default=None, sa_column=Column(TEXT))
        blob_value: bytes | None = Field(default=None, sa_column=Column(BLOB))

    # reset
    test_exists = storage.table_exists("test")
    if test_exists:
        with storage.session() as session:
            session.execute(delete(Test))
            session.commit()
    storage.create_tables()

    # insert a new object
    test_1 = Test(
        key="hello",
        value="world",
    )
    storage.set(test_1)
    result = storage.get(Test, first=True)
    assert result is not None
    assert result.key == "hello" and result.value == "world"

    # change object and update
    test_1.value = "Agently"
    storage.set(test_1)
    result = storage.get(Test, first=True)
    assert result is not None
    assert result.key == "hello" and result.value == "Agently"

    # different object with same model with same primary key
    test_2 = Test(
        key="hello",
        value="world",
    )
    storage.set(test_2)
    results = storage.get(Test)
    assert len(results) == 1
    assert results[0].key == "hello" and results[0].value == "world"

    # different object
    test_3 = Test(key="good", value="job")
    storage.set(test_3)
    results = storage.get(Test, order_by=Column("key").asc())
    assert len(results) == 2
    assert results[0].key == "good" and results[0].value == "job"


@pytest.mark.asyncio
async def test_async_sqlite():
    storage = AsyncStorage(db_url="sqlite+aiosqlite:///localstorage.db")

    class Test(SQLModel, table=True):
        __table_args__ = {"extend_existing": True}
        key: str = Field(primary_key=True)
        value: str | None = Field(default=None, sa_column=Column(TEXT))
        blob_value: bytes | None = Field(default=None, sa_column=Column(BLOB))

    # reset
    test_exists = await storage.table_exists("test")
    if test_exists:
        async with storage.session() as session:
            await session.execute(delete(Test))
            await session.commit()
    await storage.create_tables()

    # insert a new object
    test_1 = Test(
        key="hello",
        value="world",
    )
    await storage.set(test_1)
    result = await storage.get(Test, first=True)
    assert result is not None
    assert result.key == "hello" and result.value == "world"

    # change object and update
    test_1.value = "Agently"
    await storage.set(test_1)
    result = await storage.get(Test, first=True)
    assert result is not None
    assert result.key == "hello" and result.value == "Agently"

    # different object with same model with same primary key
    test_2 = Test(
        key="hello",
        value="world",
    )
    await storage.set(test_2)
    results = await storage.get(Test)
    assert len(results) == 1
    assert results[0].key == "hello" and results[0].value == "world"

    # different object
    test_3 = Test(key="good", value="job")
    await storage.set(test_3)
    results = await storage.get(Test, order_by=Column("key").asc())
    assert len(results) == 2
    assert results[0].key == "good" and results[0].value == "job"
