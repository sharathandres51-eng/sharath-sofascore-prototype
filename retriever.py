import os
import numpy as np
from pathlib import Path
from openai import OpenAI
import streamlit as st

# ---------------------------------------------------------------------------
# Client setup — mirrors how llm.py handles the API key
# ---------------------------------------------------------------------------
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY")))

KNOWLEDGE_BASE_DIR = Path(__file__).parent / "knowledge_base"

# ---------------------------------------------------------------------------
# Build the FAISS vector store once and cache it for the session.
# Using st.cache_resource so the index is built only on the first call
# and then reused across all reruns without re-embedding.
# ---------------------------------------------------------------------------
@st.cache_resource
def build_vector_store():
    """
    Loads every .txt file from the knowledge_base folder, embeds them
    using OpenAI's text-embedding-3-small model, and stores them in a
    FAISS index for fast nearest-neighbour search.

    Returns:
        index   – the FAISS flat L2 index
        docs    – list of {"name": str, "content": str} dicts
    """
    import faiss  # imported here so the rest of the module works even if faiss isn't installed yet

    docs = []
    for txt_file in sorted(KNOWLEDGE_BASE_DIR.glob("*.txt")):
        content = txt_file.read_text(encoding="utf-8").strip()
        if content:
            docs.append({"name": txt_file.stem, "content": content})

    if not docs:
        return None, []

    texts = [d["content"] for d in docs]

    # Embed all knowledge base documents in a single batched call
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    embeddings = np.array(
        [e.embedding for e in response.data],
        dtype=np.float32
    )

    # Build a simple flat L2 FAISS index (exact search — fine for 8 docs)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    return index, docs


def retrieve(query: str, top_k: int = 2) -> list[str]:
    """
    Finds the top_k most semantically relevant knowledge base documents
    for the given query string.

    Args:
        query  – the user question or topic to retrieve context for
        top_k  – number of documents to return (default 2)

    Returns:
        A list of document content strings, ordered by relevance.
    """
    index, docs = build_vector_store()

    if index is None or not docs:
        return []

    import faiss  # noqa

    # Embed the query using the same model as the knowledge base
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[query]
    )
    query_embedding = np.array(
        [response.data[0].embedding],
        dtype=np.float32
    )

    # Search — returns distances and the indices of the closest docs
    k = min(top_k, len(docs))
    _, indices = index.search(query_embedding, k)

    return [docs[i]["content"] for i in indices[0]]
