from pydantic import BaseModel, Field
from typing import Dict, Any
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