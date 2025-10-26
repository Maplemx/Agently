from agently.utils import LazyImport

LazyImport.import_package("chromadb")

import json

from chromadb.api.types import EmbeddingFunction, Documents, Embedding, Embeddings

from typing import Callable, TypedDict, Any, cast
from agently.core import BaseAgent


class ChromaDataDictOptional(TypedDict, total=False):
    metadata: dict[Any, Any]
    id: Any
    embedding: Embedding


class ChromaDataDict(ChromaDataDictOptional):
    document: str


class ChromaData:
    def __init__(
        self,
        original_data: ChromaDataDict | list[ChromaDataDict],
        *,
        embedding_function: Callable[[str | list[str]], Embeddings] | None = None,
        agent: BaseAgent | None = None,
    ):
        self._original_data = original_data if isinstance(original_data, list) else [original_data]
        if embedding_function:
            self._embedding_function = embedding_function
        elif agent:

            def embedding_function_by_agent(texts: str | list[str]) -> Embeddings:
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


class ChromaEmbeddingFunction(EmbeddingFunction):
    def __init__(
        self, *, embedding_function: Callable[[list[str]], Embeddings] | None = None, agent: BaseAgent | None = None
    ):
        if embedding_function:
            self.embedding_function = embedding_function
        elif agent:

            def embedding_function_by_agent(texts: list[str]) -> Embeddings:
                return agent.input(texts).start()

            self.embedding_function = embedding_function_by_agent
        else:
            raise ValueError(
                f"ChromaEmbeddingFunction() requires at least one definition for 'embedding_function' or 'agent'."
            )

    def __call__(self, documents: Documents) -> Embeddings:
        return self.embedding_function([document for document in documents])
