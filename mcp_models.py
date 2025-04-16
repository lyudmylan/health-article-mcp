from pydantic import BaseModel, Field, HttpUrl
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from uuid import UUID, uuid4

class MCPMessage(BaseModel):
    message_id: UUID = Field(default_factory=uuid4)
    conversation_id: UUID = Field(default_factory=uuid4)
    sender_agent: str
    recipient_agent: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload_type: str  # e.g., 'url', 'article_text', 'summary', 'terminology', 'quality_assessment'
    payload: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "123e4567-e89b-12d3-a456-426614174000",
                "conversation_id": "123e4567-e89b-12d3-a456-426614174001",
                "sender_agent": "UserAgent",
                "recipient_agent": "ArticleFetcherAgent",
                "timestamp": "2024-03-15T10:00:00Z",
                "payload_type": "url",
                "payload": {
                    "url": "https://example.com/medical-study"
                }
            }
        }

class WorkflowResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)

class Message(BaseModel):
    """Message model for processing requests"""
    url: Optional[HttpUrl] = None
    text: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.nejm.org/doi/full/10.1056/NEJMoa2118542",
                "text": None
            }
        }

class ProcessResponse(BaseModel):
    """Response model for processed articles"""
    summary: str = Field(..., description="Concise summary of the article")
    explanation: Dict[str, str] = Field(..., description="Dictionary of medical terms and their explanations")
    quality_assessment: Dict[str, Union[Dict[str, str], List[str]]] = Field(
        ...,
        description="Quality assessment metrics including study design, sample quality, etc."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary": "Regular exercise reduces cardiovascular events by 50% across all age groups.",
                "explanation": {
                    "Cardiovascular": "Relating to the heart and blood vessels",
                    "Exercise tolerance": "The ability to perform physical activity without undue fatigue"
                },
                "quality_assessment": {
                    "study_design": {"rating": "4", "explanation": "Well-designed cohort study"},
                    "overall_score": {"rating": "4.2", "explanation": "High-quality study with minor limitations"},
                    "key_limitations": ["Limited follow-up period"],
                    "recommendations": ["Consider longer follow-up study"]
                }
            }
        } 