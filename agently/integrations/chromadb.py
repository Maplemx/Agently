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


from agently.utils import LazyImport

LazyImport.import_package("chromadb")

from typing import Literal, Callable, TypedDict, Any, TYPE_CHECKING, overload
from itertools import zip_longest

from chromadb import Client as ChromaDBClient
from chromadb.config import Settings
from chromadb.api.types import EmbeddingFunction

if TYPE_CHECKING:
    from chromadb.api.types import (
        Documents,
        Embedding,
        Embeddings,
        QueryResult,
        Schema,
        DataLoader,
        Loadable,
        Where,
        WhereDocument,
    )
    from chromadb.api.collection_configuration import CreateCollectionConfiguration
    from chromadb.api import ClientAPI
    from agently.core import BaseAgent


class ChromaDataDictOptional(TypedDict, total=False):
    metadata: dict[Any, Any]
    id: Any
    embedding: "Embedding"


class ChromaDataDict(ChromaDataDictOptional):
    document: str


class ChromaData:
    def __init__(
        self,
        original_data: ChromaDataDict | list[ChromaDataDict],
        *,
        embedding_function: "Callable[[str | list[str]], Embeddings] | None" = None,
        agent: "BaseAgent | None" = None,
    ):
        self._original_data = original_data if isinstance(original_data, list) else [original_data]
        if embedding_function:
            self._embedding_function = embedding_function
        elif agent:

            def embedding_function_by_agent(texts: str | list[str]) -> "Embeddings":
                return agent.input(texts).start()

            self._embedding_function = embedding_function_by_agent
        else:
            self._embedding_function = None
        self._chroma_data = {
            "documents": [],
            "metadatas": [],
            "ids": [],
            "embeddings": [],
        }
        if self._embedding_function is not None:
            documents = [data["document"] for data in self._original_data]
            embeddings = self._embedding_function(documents)
            self._chroma_data["embeddings"] = embeddings
            for index, data in enumerate(self._original_data):
                data["embedding"] = embeddings[index]
        else:
            del self._chroma_data["embeddings"]
        for index, data in enumerate(self._original_data):
            self._chroma_data["documents"].append(data["document"])
            self._chroma_data["metadatas"].append(data["metadata"] if "metadata" in data else None)
            self._chroma_data["ids"].append(data["id"] if "id" in data else str(index))

    def get_kwargs(self):
        return self._chroma_data

    def get_original_data(self):
        return self._original_data


class ChromaResults:
    def __init__(
        self,
        *,
        queries: str | list[str],
        results: "QueryResult",
        distance: float | None = None,
    ):
        if isinstance(queries, str):
            queries = [queries]

        ids = results.get("ids") or []
        documents = results.get("documents")
        metadatas = results.get("metadatas")
        distances = results.get("distances")

        if ids and len(queries) != len(ids):
            raise ValueError(
                f"The length of queries does not equal the length of results['ids'].\nQueries: {queries}\nIds: {ids}"
            )

        self._chroma_results = results
        self._results: dict[str, list[dict]] = {}

        doc_iter = documents if documents is not None else []
        meta_iter = metadatas if metadatas is not None else []
        dist_iter = distances if distances is not None else []

        for query, row_ids, row_documents, row_metadatas, row_distances in zip_longest(
            queries, ids, doc_iter, meta_iter, dist_iter, fillvalue=None
        ):
            row_ids = row_ids or []
            query_results: list[dict[str, Any]] = []
            for id_, doc, meta, dist in zip_longest(
                row_ids, row_documents or [], row_metadatas or [], row_distances or [], fillvalue=None
            ):
                query_result = {"id": id_, "document": doc, "metadata": meta, "distance": dist}
                if distance is None:
                    query_results.append(query_result)
                else:
                    if isinstance(dist, (int, float)) and dist < distance:
                        query_results.append(query_result)

            if query:
                self._results[query] = query_results

    def get_original_results(self):
        return self._chroma_results

    def get(self, *, simplify_single_result: bool = False):
        if simplify_single_result:
            results = list(self._results.values())
            if len(results) == 1:
                return results[0]
        return self._results


class ChromaEmbeddingFunction(EmbeddingFunction):
    def __init__(
        self,
        *,
        embedding_agent: "BaseAgent",
    ):
        def embedding_function_by_agent(texts: list[str]) -> "Embeddings":
            return embedding_agent.input(texts).start()

        self.embedding_function = embedding_function_by_agent

    def __call__(self, documents: "Documents | list[str] | str") -> "Embeddings":
        if isinstance(documents, str):
            documents = [documents]
        return self.embedding_function([document for document in documents])


class ChromaCollection:

    def __init__(
        self,
        collection_name: str,
        *,
        conn: "ClientAPI | None" = None,
        schema: "Schema | None" = None,
        configuration: "CreateCollectionConfiguration | None" = None,
        metadata: dict[str, Any] | None = None,
        embedding_agent: "BaseAgent | None" = None,
        data_loader: "DataLoader[Loadable] | None" = None,
        get_or_create: bool = False,
        hnsw_space: Literal["l2", "cosine", "ip"] = "cosine",
    ):
        if conn is None:
            conn = ChromaDBClient(Settings(anonymized_telemetry=False))

        if metadata is None:
            metadata = {}

        metadata["hnsw:space"] = hnsw_space

        self.embedding_function = (
            ChromaEmbeddingFunction(embedding_agent=embedding_agent) if embedding_agent is not None else None
        )

        self._collection = conn.create_collection(
            collection_name,
            schema=schema,
            configuration=configuration,
            metadata=metadata,
            embedding_function=self.embedding_function,
            data_loader=data_loader,
            get_or_create=get_or_create,
        )

    def add(
        self,
        data: ChromaDataDict | list[ChromaDataDict] | ChromaData,
        *,
        embedding_function: "Callable[[str | list[str]], Embeddings] | None" = None,
    ):
        embedding_function = embedding_function or self.embedding_function
        if embedding_function is None:
            raise NotImplementedError(
                f"Embedding function must be assigned either in ChromaCollection initialize or .add() method."
            )
        if not isinstance(data, ChromaData):
            data = ChromaData(data, embedding_function=embedding_function)
        self._collection.add(**data.get_kwargs())
        return self

    @overload
    def query(
        self,
        query_or_queries: str,
        *,
        embedding_function: "Callable[[str | list[str]], Embeddings] | None" = None,
        top_n: int | None = None,
        where: "Where | None" = None,
        where_document: "WhereDocument | None" = None,
        distance: float | None = None,
    ) -> list[dict[str, Any]]: ...

    @overload
    def query(
        self,
        query_or_queries: list[str],
        *,
        embedding_function: "Callable[[str | list[str]], Embeddings] | None" = None,
        top_n: int | None = None,
        where: "Where | None" = None,
        where_document: "WhereDocument | None" = None,
        distance: float | None = None,
    ) -> dict[str, list[dict[str, Any]]]: ...

    def query(
        self,
        query_or_queries: str | list[str],
        *,
        embedding_function: "Callable[[str | list[str]], Embeddings] | None" = None,
        top_n: int | None = None,
        where: "Where | None" = None,
        where_document: "WhereDocument | None" = None,
        distance: float | None = None,
    ):
        embedding_function = embedding_function or self.embedding_function
        if embedding_function is None:
            raise NotImplementedError(
                f"Embedding function must be assigned either in ChromaCollection initialize or .query() method."
            )
        if not isinstance(query_or_queries, list):
            query_or_queries = [query_or_queries]
        return ChromaResults(
            queries=query_or_queries,
            results=self._collection.query(
                query_embeddings=embedding_function(query_or_queries),
                n_results=top_n or 10,
                where=where,
                where_document=where_document,
            ),
            distance=distance,
        ).get(simplify_single_result=True)

    def query_embeddings(
        self,
        embeddings_dict: dict[str, "Embedding"],
        *,
        top_n: int | None = None,
        where: "Where | None" = None,
        where_document: "WhereDocument | None" = None,
        distance: float | None = None,
    ):
        queries = [query for query in embeddings_dict.keys()]
        embeddings = [embeddings for embeddings in embeddings_dict.values()]
        return ChromaResults(
            queries=queries,
            results=self._collection.query(
                query_embeddings=embeddings,
                n_results=top_n or 10,
                where=where,
                where_document=where_document,
            ),
            distance=distance,
        ).get(simplify_single_result=True)
