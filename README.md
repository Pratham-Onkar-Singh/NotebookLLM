# 📚 PDF AI (NotebookLLM Clone)

This platform allows users to upload PDF and TXT documents and conversationally query their contents. It utilizes an advanced LLM pipeline grounded strictly in retrieved context to ensure accurate responses and prevent AI hallucination.

## ✨ Features

*   **Document Processing:** Seamlessly upload and ingest PDF and TXT files for analysis.
*   **Strict Grounding:** The AI only answers based on the provided document context, eliminating fabricated responses.
*   **High-Speed Retrieval:** Sub-second top-10 cosine similarity search for instant query resolution.
*   **Async Processing:** Highly concurrent backend handling document ingestion and routing without blocking.
*   **Responsive UI:** Clean, modern, and mobile-friendly interface.

## 🛠️ Tech Stack

**Frontend**
*   **React** (via Vite)
*   **Tailwind CSS** 
*   **JavaScript / JSX**

**Backend & AI**
*   **Python 3**
*   **FastAPI** 
*   **LangChain** (LLM Orchestration)
*   **Qdrant** (Vector Database)
*   **Google Gemini Embeddings** (3072-dimensional vectors)

## 📁 Project Structure

The repository is organized into distinct frontend and backend services:

### Backend
The backend is a robust FastAPI application handling the RAG engine and API routing.
*   `backend/main.py`: Application entry point[cite: 2].
*   `backend/requirements.txt`: Python dependencies[cite: 2].
*   `backend/api/routers/chat.py`: API endpoints for handling conversational queries[cite: 2].
*   `backend/api/schemas/requests.py`: Pydantic models for request validation[cite: 2].
*   `backend/api/services/prompts.py`: System prompt templates for strict grounding[cite: 2].
*   `backend/api/services/rag_engine.py`: Core logic for recursive chunking, vector embedding, and Qdrant indexing[cite: 2].

### Frontend
The frontend is a Vite-powered React application.
*   `frontend/index.html`: Main HTML template[cite: 2].
*   `frontend/package.json` & `frontend/package-lock.json`: Node dependencies[cite: 2].
*   `frontend/vite.config.js`: Vite configuration and bundling[cite: 2].
*   `frontend/tailwind.config.js` & `frontend/postcss.config.js`: Tailwind CSS configuration[cite: 2].
*   `frontend/src/App.jsx` & `frontend/src/main.jsx`: Core React components and application rendering logic[cite: 2].
*   `frontend/src/index.css`: Global stylesheet[cite: 2].
