import os

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from .ollama import embeddings

client = QdrantClient(host=os.getenv("QDRANT_HOST", "localhost"), port=6333)


def get_vector_store(collection_name: str):
    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )


doc_store = get_vector_store("documents")
feedback_store = get_vector_store("self_learning")
