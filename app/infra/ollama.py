import os

from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.26.109:11434")

# 單例模式初始化
embeddings = OllamaEmbeddings(
    base_url=OLLAMA_URL,
    model=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest"),
)
llm = Ollama(
    base_url=OLLAMA_URL,
    model=os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b"),
    temperature=0.1,
)
