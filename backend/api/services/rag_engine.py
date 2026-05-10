import os
import uuid
from typing import List, Dict
from dotenv import load_dotenv

from huggingface_hub import AsyncInferenceClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from .prompts import RAG_GENERATION_PROMPT

load_dotenv()

hf_client = AsyncInferenceClient(
    model=os.getenv("HUGGINGFACE_MODEL_ID"), api_key=os.getenv("HUGGINGFACE_API_KEY")
)

# qdrant = QdrantClient(url=os.getenv("QDRANT_URL"))
# Connect to Qdrant Cloud using credentials from .env
qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)
qdrant.set_model("sentence-transformers/all-MiniLM-L6-v2")

chat_histories: Dict[str, List[Dict[str, str]]] = {}

# Text splitter for chunking documents
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=600, chunk_overlap=100, separators=["\n\n", "\n", ". ", " "]
)


async def process_and_index_document(text: str) -> str:
    """Chunks the text, generates embeddings, and stores them in Qdrant."""
    if not text.strip():
        raise ValueError("Document contains no readable text.")
    session_id = str(uuid.uuid4())

    chunks = text_splitter.split_text(text)
    qdrant.recreate_collection(
        collection_name=session_id, vectors_config=qdrant.get_fastembed_vector_params()
    )

    qdrant.add(
        collection_name=session_id, documents=chunks, ids=list(range(len(chunks)))
    )
    chat_histories[session_id] = []

    return session_id


async def retrieve_relevant_context(session_id: str, query: str, top_k: int = 4) -> str:
    """Searches the vector database for the most relevant document chunks."""
    try:
        search_results = qdrant.query(
            collection_name=session_id, query_text=query, limit=top_k
        )

        # Extract the text from the search results
        retrieved_texts = [hit.document for hit in search_results if hit.document]
        return "\n\n---\n\n".join(retrieved_texts)
    except Exception as e:
        print(f"Search error: {e}")
        return ""


def format_history(session_id: str) -> str:
    """Formats the past conversation into a readable string for the LLM."""
    history = chat_histories.get(session_id, [])
    if not history:
        return "No prior conversation."

    formatted = []
    for msg in history[
        -4:
    ]:  # Only keep the last 4 messages for context window efficiency
        formatted.append(f"{msg['role'].capitalize()}: {msg['content']}")

    return "\n".join(formatted)


async def generate_rag_response(session_id: str, query: str) -> str:
    """Coordinates retrieval and LLM generation to answer the user's query."""
    context = await retrieve_relevant_context(session_id, query)
    history = format_history(session_id)

    final_prompt = RAG_GENERATION_PROMPT.format(
        context=context if context else "[NO CONTEXT FOUND]",
        history=history,
        question=query,
    )
    response = await hf_client.chat_completion(
        messages=[{"role": "user", "content": final_prompt}],
        max_tokens=500,
        temperature=0.1,
    )

    answer = response.choices[0].message.content
    if session_id in chat_histories:
        chat_histories[session_id].append({"role": "user", "content": query})
        chat_histories[session_id].append({"role": "assistant", "content": answer})

    return answer


def cleanup_session(session_id: str):
    chat_histories.pop(session_id, None)
    try:
        qdrant.delete_collection(collection_name=session_id)
    except Exception:
        pass
