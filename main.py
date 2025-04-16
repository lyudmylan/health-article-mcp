from fastapi import FastAPI, HTTPException, Request
import os
import logging
from openai import OpenAI
from mcp_models import MCPMessage, WorkflowResponse
from agents import fetch_article, summarize_text, explain_terminology, assess_study_quality, ArticleFetchError
from error_handlers import retry_with_backoff, validate_url, handle_api_error, RetryableError, NetworkError
from rate_limiter import rate_limit, cached
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

# Configure rate limits
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# Configure cache TTL (in seconds)
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))  # 1 hour default

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

@retry_with_backoff(
    max_retries=3,
    retryable_exceptions=(RetryableError, NetworkError)
)
@cached(ttl=CACHE_TTL)
async def process_url(message: MCPMessage) -> MCPMessage:
    """Handle URL processing by the ArticleFetcher agent"""
    try:
        # Validate URL before processing
        url = message.payload["url"]
        validate_url(url)
        
        article_text = fetch_article(url)
        return create_mcp_message(
            conversation_id=message.conversation_id,
            sender_agent="ArticleFetcherAgent",
            recipient_agent="SummarizerAgent",
            payload_type="article_text",
            payload={"text": article_text}
        )
    except ArticleFetchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in process_url: {str(e)}")
        raise NetworkError(str(e))

@retry_with_backoff(max_retries=2)
@cached(ttl=CACHE_TTL)
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
        raise RetryableError(str(e))

@retry_with_backoff(max_retries=2)
@cached(ttl=CACHE_TTL)
async def process_terminology(message: MCPMessage) -> MCPMessage:
    """Handle terminology explanation by the Terminology Explainer agent"""
    try:
        terminology_dict = explain_terminology(message.payload["text"], app.state.openai_client)
        return create_mcp_message(
            conversation_id=message.conversation_id,
            sender_agent="TerminologyExplainerAgent",
            recipient_agent="ResponseFormatterAgent",
            payload_type="terminology",
            payload={"terminology": terminology_dict}
        )
    except Exception as e:
        logger.error(f"Error in process_terminology: {str(e)}")
        raise RetryableError(str(e))

@retry_with_backoff(max_retries=2)
@cached(ttl=CACHE_TTL)
async def process_quality_assessment(message: MCPMessage) -> MCPMessage:
    """Handle study quality assessment by the Quality Assessor agent"""
    try:
        quality_assessment = assess_study_quality(message.payload["text"], app.state.openai_client)
        return create_mcp_message(
            conversation_id=message.conversation_id,
            sender_agent="QualityAssessorAgent",
            recipient_agent="ResponseFormatterAgent",
            payload_type="quality_assessment",
            payload={"assessment": quality_assessment}
        )
    except Exception as e:
        logger.error(f"Error in process_quality_assessment: {str(e)}")
        raise RetryableError(str(e))

@app.post("/workflow/process", response_model=WorkflowResponse)
@rate_limit(max_requests=RATE_LIMIT_MAX_REQUESTS, time_window=RATE_LIMIT_WINDOW)
async def process_workflow(request: Request, message: MCPMessage) -> WorkflowResponse:
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
        
        # Third step: Explain terminology
        terminology_result = await process_terminology(fetcher_result)
        
        # Fourth step: Assess study quality
        quality_result = await process_quality_assessment(fetcher_result)
        
        # Return the combined results
        return WorkflowResponse(
            success=True,
            message="Article processed successfully",
            data={
                "message_id": str(summarizer_result.message_id),
                "summary": summarizer_result.payload["summary"],
                "terminology": terminology_result.payload["terminology"],
                "quality_assessment": quality_result.payload["assessment"]
            }
        )
            
    except Exception as e:
        raise handle_api_error(e)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 