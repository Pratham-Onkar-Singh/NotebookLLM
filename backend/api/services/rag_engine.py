import os
import json
import uuid
import asyncio
from typing import List, Dict, Tuple
from dotenv import load_dotenv

from huggingface_hub import AsyncInferenceClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient

from .prompts import (
    RAG_GENERATION_PROMPT,
    QUERY_OPTIMIZATION_PROMPT,
    HYDE_PROMPT,
    RELEVANCE_JUDGE_PROMPT,
)

load_dotenv()


# ---------------------------------------------------------------------------
# Configuration — advanced-RAG knobs.
# Every stage can be toggled independently so you can trade speed for accuracy:
# more stages = better answers but more LLM round-trips / latency.
# ---------------------------------------------------------------------------
def _flag(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


ENABLE_QUERY_REWRITE = _flag("ENABLE_QUERY_REWRITE", "true")
ENABLE_HYDE = _flag("ENABLE_HYDE", "false")
ENABLE_RERANK = _flag("ENABLE_RERANK", "true")
ENABLE_LLM_JUDGE = _flag("ENABLE_LLM_JUDGE", "true")

# How many candidates to pull from the vector DB before re-ranking, and how many
# survive into the final context window. Over-retrieving + re-ranking beats just
# trusting the raw vector similarity top-k.
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "10"))
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "4"))

# Chunking — chunk size & overlap are a tradeoff: smaller chunks = sharper
# retrieval but more fragmentation; larger overlap = better continuity but more
# tokens. Tunable from the environment.
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "600"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))
RERANK_MODEL = os.getenv("RERANK_MODEL", "Xenova/ms-marco-MiniLM-L-6-v2")


hf_client = AsyncInferenceClient(
    model=os.getenv("HUGGINGFACE_MODEL_ID"), api_key=os.getenv("HUGGINGFACE_API_KEY")
)

qdrant = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
qdrant.set_model("sentence-transformers/all-MiniLM-L6-v2")

chat_histories: Dict[str, List[Dict[str, str]]] = {}

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separators=["\n\n", "\n", ". ", " "]
)

# Cross-encoder re-ranker is loaded lazily (it downloads/initialises a model the
# first time) so the API can boot fast and only pay the cost if re-ranking is on.
_cross_encoder = None


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        _cross_encoder = TextCrossEncoder(model_name=RERANK_MODEL)
    return _cross_encoder


async def _llm(prompt: str, max_tokens: int = 500, temperature: float = 0.1) -> str:
    """Thin helper around the HF chat endpoint for one-shot completions."""
    response = await hf_client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()


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


# ---------------------------------------------------------------------------
# Stage 1 — Query rewriting / translation using a small LLM.
# Resolves pronouns against history and decides whether retrieval is even needed
# (greetings/thanks don't need a vector search — a cheap bottleneck to remove).
# ---------------------------------------------------------------------------
async def rewrite_query(session_id: str, query: str) -> Tuple[bool, str]:
    """Returns (needs_search, search_query)."""
    if not ENABLE_QUERY_REWRITE:
        return True, query

    history = format_history(session_id)
    prompt = (
        QUERY_OPTIMIZATION_PROMPT
        + f"\n\nChat History:\n{history}\n\nUser: \"{query}\"\nOutput:"
    )
    try:
        raw = await _llm(prompt, max_tokens=120, temperature=0.0)
        # Be forgiving about markdown fences / stray text around the JSON.
        raw = raw.replace("```json", "").replace("```", "").strip()
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start : end + 1])
        needs_search = bool(data.get("needs_search", True))
        search_query = data.get("search_query") or query
        return needs_search, search_query
    except Exception as e:
        # Fail open: if rewriting breaks, fall back to the raw query + retrieval.
        print(f"Query rewrite failed, using raw query: {e}")
        return True, query


# ---------------------------------------------------------------------------
# Stage 2 — HyDE (Hypothetical Document Embeddings).
# Embed a hypothetical *answer* instead of the question, since answers sit closer
# to real document chunks in vector space than questions do.
# ---------------------------------------------------------------------------
async def generate_hyde_document(search_query: str) -> str:
    try:
        hypo = await _llm(HYDE_PROMPT.format(question=search_query), max_tokens=160)
        # Append the original query so we keep its keywords in the embedding.
        return f"{hypo}\n\n{search_query}"
    except Exception as e:
        print(f"HyDE failed, using raw query: {e}")
        return search_query


# ---------------------------------------------------------------------------
# Stage 3 — Retrieve a wide candidate set from Qdrant.
# ---------------------------------------------------------------------------
async def retrieve_candidates(session_id: str, retrieval_text: str, top_k: int) -> List[str]:
    try:
        hits = qdrant.query(
            collection_name=session_id, query_text=retrieval_text, limit=top_k
        )
        return [hit.document for hit in hits if hit.document]
    except Exception as e:
        print(f"Search error: {e}")
        return []


# ---------------------------------------------------------------------------
# Stage 4 — Cross-encoder re-ranking.
# The vector search gives recall; the cross-encoder gives precision by scoring
# (query, chunk) pairs jointly. Runs in a thread so it doesn't block the loop.
# ---------------------------------------------------------------------------
async def rerank(query: str, documents: List[str], top_n: int) -> List[str]:
    if not documents:
        return []
    if not ENABLE_RERANK:
        return documents[:top_n]
    try:
        encoder = _get_cross_encoder()
        scores = await asyncio.to_thread(lambda: list(encoder.rerank(query, documents)))
        ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in ranked[:top_n]]
    except Exception as e:
        print(f"Re-ranking failed, falling back to vector order: {e}")
        return documents[:top_n]


# ---------------------------------------------------------------------------
# Stage 5 — LLM judge / Corrective RAG.
# Grade whether the assembled context can actually answer the question. If not,
# we drop it so the generator gives the honest "not found" answer instead of
# hallucinating from loosely-related chunks.
# ---------------------------------------------------------------------------
async def context_is_relevant(query: str, context: str) -> bool:
    if not ENABLE_LLM_JUDGE or not context:
        return bool(context)
    try:
        verdict = await _llm(
            RELEVANCE_JUDGE_PROMPT.format(question=query, context=context),
            max_tokens=4,
            temperature=0.0,
        )
        return verdict.strip().lower().startswith("y")
    except Exception as e:
        print(f"Relevance judge failed, keeping context: {e}")
        return True


def format_history(session_id: str) -> str:
    """Formats the past conversation into a readable string for the LLM."""
    history = chat_histories.get(session_id, [])
    if not history:
        return "No prior conversation."

    formatted = []
    for msg in history[-4:]:  # Keep only the last 4 messages for context efficiency
        formatted.append(f"{msg['role'].capitalize()}: {msg['content']}")

    return "\n".join(formatted)


async def generate_rag_response(session_id: str, query: str) -> str:
    """Coordinates the advanced retrieval pipeline and LLM generation."""
    history = format_history(session_id)

    # Stage 1: rewrite + decide whether retrieval is needed.
    needs_search, search_query = await rewrite_query(session_id, query)

    context = ""
    if needs_search:
        # Stage 2: HyDE expansion (optional).
        retrieval_text = (
            await generate_hyde_document(search_query) if ENABLE_HYDE else search_query
        )

        # Stage 3 + 4: over-retrieve, then re-rank down to the final set.
        candidates = await retrieve_candidates(session_id, retrieval_text, RETRIEVAL_TOP_K)
        top_chunks = await rerank(search_query, candidates, RERANK_TOP_N)
        assembled = "\n\n---\n\n".join(top_chunks)

        # Stage 5: corrective check — keep context only if the judge approves.
        if await context_is_relevant(search_query, assembled):
            context = assembled

    final_prompt = RAG_GENERATION_PROMPT.format(
        context=context if context else "[NO CONTEXT FOUND]",
        history=history,
        question=query,
    )
    answer = await _llm(final_prompt, max_tokens=500, temperature=0.1)

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
