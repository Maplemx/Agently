from agently import Agently
from agently.integrations.chromadb import ChromaCollection

embedding = Agently.create_agent()
embedding.set_settings(
    "OpenAICompatible",
    {
        "model": "qwen3-embedding:0.6b",
        "base_url": "http://127.0.0.1:11434/v1/",
        "auth": "nothing",
        "model_type": "embeddings",
    },
)

collection = ChromaCollection(
    collection_name="demo",
    embedding_agent=embedding,
)

collection.add(
    [
        {
            "document": "Book about Dogs",
            "metadata": {"book_name": "🐶"},
        },
        {
            "document": "Book about cars",
            "metadata": {"book_name": "🚗"},
        },
        {
            "document": "Book about vehicles",
            "metadata": {"book_name": "🚘"},
        },
        {
            "document": "Book about birds",
            "metadata": {"book_name": "🐦‍⬛"},
        },
    ]
)

results = collection.query("Things that can move really fast")
print(results)
