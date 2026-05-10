from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    """Schema for incoming chat messages from the frontend."""
    session_id: str = Field(..., description="The unique identifier for the uploaded document session.")
    query: str = Field(..., description="The question the user is asking about the document.")

class SearchDecision(BaseModel):
    """Schema used by the LLM to decide if a database search is required."""
    needs_search: bool = Field(..., description="True if the query requires searching the vector database.")
    search_query: Optional[str] = Field(None, description="The reformulated query optimized for vector search.")