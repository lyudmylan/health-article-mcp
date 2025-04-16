from fastapi import FastAPI, HTTPException
import os
import logging
from openai import OpenAI
from mcp_models import MCPMessage, WorkflowResponse
from agents import fetch_article, summarize_text, ArticleFetchError
from uuid import uuid4

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Health Article MCP",
    description="Multi-Agent System for Processing Health Articles",
    version="1.0.0"
)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key and not os.getenv("TESTING"):
    raise ValueError("OPENAI_API_KEY environment variable is not set")

openai_client = OpenAI(api_key=api_key or "test-key")
app.state.openai_client = openai_client

def create_mcp_message(
    conversation_id: str,
    sender_agent: str,
    recipient_agent: str,
    payload_type: str,
    payload: dict
) -> MCPMessage:
    """Helper function to create MCP messages"""
    return MCPMessage(
        conversation_id=conversation_id,
        sender_agent=sender_agent,
        recipient_agent=recipient_agent,
        payload_type=payload_type,
        payload=payload
    )

async def process_url(message: MCPMessage) -> MCPMessage:
    """Handle URL processing by the ArticleFetcher agent"""
    try:
        article_text = fetch_article(message.payload["url"])
        return create_mcp_message(
            conversation_id=message.conversation_id,
            sender_agent="ArticleFetcherAgent",
            recipient_agent="SummarizerAgent",
            payload_type="article_text",
            payload={"text": article_text}
        )
    except ArticleFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in process_url: {str(e)}")
        raise

async def process_article_text(message: MCPMessage) -> MCPMessage:
    """Handle article text processing by the Summarizer agent"""
    try:
        logger.info(f"Processing article text with OpenAI client: {app.state.openai_client}")
        summary = summarize_text(message.payload["text"], app.state.openai_client)
        return create_mcp_message(
            conversation_id=message.conversation_id,
            sender_agent="SummarizerAgent",
            recipient_agent="ResponseFormatterAgent",
            payload_type="summary",
            payload={"summary": summary}
        )
    except Exception as e:
        logger.error(f"Error in process_article_text: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflow/process", response_model=WorkflowResponse)
async def process_workflow(message: MCPMessage) -> WorkflowResponse:
    try:
        # Log received message
        logger.info(f"Received message: {message.model_dump_json(indent=2)}")
        
        # Process based on payload_type
        if message.payload_type != "url":
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported payload type: {message.payload_type}"
            )
            
        # First step: Fetch article
        fetcher_result = await process_url(message)
        
        # Second step: Generate summary
        summarizer_result = await process_article_text(fetcher_result)
        
        # Return the summary as the final result
        return WorkflowResponse(
            success=True,
            message="Article processed successfully",
            data={
                "message_id": str(summarizer_result.message_id),
                "summary": summarizer_result.payload["summary"]
            }
        )
            
    except HTTPException as e:
        logger.error(f"Error in workflow processing: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 