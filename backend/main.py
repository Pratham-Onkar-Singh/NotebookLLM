import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers.chat import router as chat_router

app = FastAPI(
    title="Notebook RAG API",
    description="A customized RAG pipeline for document-grounded conversations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register our chat and document processing routes
app.include_router(chat_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Notebook RAG API is up and running!"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)