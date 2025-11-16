# Copyright 2023-2025 AgentEra(Agently.Tech)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from typing import (
    Sequence,
    Type,
    TypeVar,
    Any,
    Literal,
    overload,
    cast,
    TYPE_CHECKING,
)
from contextlib import asynccontextmanager

from .LazyImport import LazyImport

LazyImport.import_package("sqlmodel")
LazyImport.import_package("sqlalchemy")

from sqlmodel import SQLModel, select, inspect, create_engine, Session  # type: ignore
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker  # type: ignore
from sqlalchemy.sql import ColumnElement  # type: ignore

from .RuntimeData import RuntimeData

T = TypeVar("T", bound=SQLModel)


class AsyncStorage:
    def __init__(self, parent_settings: RuntimeData | None = None, *, db_url: str | None = None):
        self.settings = RuntimeData(name="Storage-Settings", parent=parent_settings).namespace("storage")

        self.db_url = self.settings.get("db_url", db_url)
        if not self.db_url:
            raise NotImplementedError(
                "Missing database url: tried both key 'db_url' in settings and keyword argument 'db_url'"
            )
        if "://" not in self.db_url:
            raise ValueError(
                "Incorrect database url format: please follow format `dialect+driver://username:password@host:port/database`.\n"
                "Example: 'sqlite:///localstorage.db', 'sqlite+aiosqlite:///localstorage.db'\n"
                "Document: https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls"
            )
        if self.db_url.startswith("sqlite"):
            os.makedirs(os.path.dirname(self.db_url.split("://", 1)[1]), exist_ok=True)

        self.engine = create_async_engine(self.db_url, echo=False)

    @asynccontextmanager
    async def session(self):
        async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with cast(AsyncSession, async_session()) as session:
            yield session

    async def table_exists(self, table_name: str) -> bool:
        def do_check(sync_conn):
            inspector = inspect(sync_conn)
            return table_name in inspector.get_table_names()

        async with self.session() as session:
            conn = await session.connection()
            return await conn.run_sync(do_check)

    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def set(self, objects: SQLModel | list[SQLModel]):
        async with self.session() as session:
            try:
                if isinstance(objects, list):
                    for object in objects:
                        await session.merge(object)
                else:
                    await session.merge(objects)
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e

    @overload
    async def get(
        self,
        model: Type[T],
        *,
        where: ColumnElement[bool] | list[ColumnElement[bool]] | None = None,
        first: Literal[True],
        limit: int | None = None,
        offset: int | None = None,
        order_by: ColumnElement[Any] | None = None,
    ) -> T | None:
        pass

    @overload
    async def get(
        self,
        model: Type[T],
        *,
        where: ColumnElement[bool] | list[ColumnElement[bool]] | None = None,
        first: Literal[False],
        limit: int | None = None,
        offset: int | None = None,
        order_by: ColumnElement[Any] | None = None,
    ) -> Sequence[T] | None: ...

    @overload
    async def get(
        self,
        model: Type[T],
        *,
        where: ColumnElement[bool] | list[ColumnElement[bool]] | None = None,
        first: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        order_by: ColumnElement[Any] | None = None,
    ): ...

    async def get(
        self,
        model: Type[T],
        *,
        where: ColumnElement[bool] | list[ColumnElement[bool]] | None = None,
        first: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        order_by: ColumnElement[Any] | None = None,
    ):
        async with self.session() as session:
            query = select(model)
            if where is not None:
                if isinstance(where, list):
                    for condition in where:
                        query = query.where(condition)
                else:
                    query = query.where(where)
            if order_by is not None:
                query = query.order_by(order_by)
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            results = await session.execute(query)
            if first:
                return results.scalars().first()
            else:
                return results.scalars().all()


class Storage:
    def __init__(self, parent_settings: RuntimeData | None = None, *, db_url: str | None = None):
        self.settings = RuntimeData(name="Storage-Settings", parent=parent_settings).namespace("storage")

        self.db_url = self.settings.get("db_url", db_url)
        if not self.db_url:
            raise NotImplementedError(
                "Missing database url: tried both key 'db_url' in settings and keyword argument 'db_url'"
            )
        if "://" not in self.db_url:
            raise ValueError(
                "Incorrect database url format: please follow format `dialect+driver://username:password@host:port/database`.\n"
                "Example: 'sqlite:///localstorage.db', 'sqlite+aiosqlite:///localstorage.db'\n"
                "Document: https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls"
            )
        if self.db_url.startswith("sqlite"):
            os.makedirs(os.path.dirname(self.db_url.split("://", 1)[1]), exist_ok=True)

        self.engine = create_engine(self.db_url, echo=False)

    def table_exists(self, table_name: str) -> bool:
        inspector = inspect(self.engine)
        return inspector.has_table(table_name)

    def create_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def session(self):
        return Session(self.engine)

    def set(self, objects: SQLModel | list[SQLModel]):
        with self.session() as session:
            try:
                if isinstance(objects, list):
                    for object in objects:
                        session.merge(object)
                else:
                    session.merge(objects)
                session.commit()
            except Exception as e:
                session.rollback()
                raise e

    @overload
    def get(
        self,
        model: Type[T],
        *,
        where: ColumnElement[bool] | list[ColumnElement[bool]] | None = None,
        first: Literal[True],
        limit: int | None = None,
        offset: int | None = None,
        order_by: ColumnElement[Any] | None = None,
    ) -> T | None:
        pass

    @overload
    def get(
        self,
        model: Type[T],
        *,
        where: ColumnElement[bool] | list[ColumnElement[bool]] | None = None,
        first: Literal[False],
        limit: int | None = None,
        offset: int | None = None,
        order_by: ColumnElement[Any] | None = None,
    ) -> Sequence[T]: ...

    @overload
    def get(
        self,
        model: Type[T],
        *,
        where: ColumnElement[bool] | list[ColumnElement[bool]] | None = None,
        first: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        order_by: ColumnElement[Any] | None = None,
    ): ...

    def get(
        self,
        model: Type[T],
        *,
        where: ColumnElement[bool] | list[ColumnElement[bool]] | None = None,
        first: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        order_by: ColumnElement[Any] | None = None,
    ):
        with self.session() as session:
            query = select(model)
            if where is not None:
                if isinstance(where, list):
                    for condition in where:
                        query = query.where(condition)
                else:
                    query = query.where(where)
            if order_by is not None:
                query = query.order_by(order_by)
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            results = session.exec(query)
            if first:
                return results.first()
            else:
                return results.all()
