import pdfplumber
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Path

from api.schemas.requests import ChatRequest
from api.services.rag_engine import (
    process_and_index_document,
    generate_rag_response,
    cleanup_session
)

router = APIRouter(tags=["Chat & Documents"])

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported.")
    try:
        text_content = ""
        if file.filename.endswith(".pdf"):
            with pdfplumber.open(file.file) as pdf:
                text_content = "\n".join(page.extract_text() or "" for page in pdf.pages)
        else:
            content_bytes = await file.read()
            text_content = content_bytes.decode("utf-8")
            
        session_id = await process_and_index_document(text_content)
        return {"session_id": session_id, "message": "Document indexed successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@router.post("/upload-text")
async def upload_raw_text(text: str = Form(...)):
    """Handles raw text pasted directly by the user."""
    try:
        session_id = await process_and_index_document(text)
        return {"session_id": session_id, "message": "Text indexed successfully."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/chat")
async def chat_with_document(request: ChatRequest):
    try:
        answer = await generate_rag_response(request.session_id, request.query)
        return {"answer": answer}
    except Exception as e:
        print("\n" + "="*20 + " HUGGING FACE ERROR " + "="*20)
        print(str(e))
        print("="*60 + "\n")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
async def delete_session(session_id: str = Path(...)):
    cleanup_session(session_id)
    return {"message": f"Session {session_id} cleaned up."}