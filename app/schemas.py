from pydantic import BaseModel

class SalesInsightResponse(BaseModel):
    """Response model for sales insights endpoint"""
    answer: str
    context_used: str