import logging
import os
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel, field_validator, model_validator
from pydantic_settings import BaseSettings
import aiohttp
import json
import openai
from bs4 import BeautifulSoup
import validators
from functools import lru_cache
import uuid
from contextlib import asynccontextmanager
from openai.error import OpenAIError

# Custom exceptions
class ArticleProcessingError(Exception):
    """Base exception class for article processing errors.
    
    This is the parent class for all article-related exceptions in the system.
    """
    pass

class ArticleFetchError(ArticleProcessingError):
    """Exception raised when article fetching fails.
    
    This exception is raised when there are issues retrieving an article,
    such as network errors, 404s, or invalid content.
    """
    pass

class ArticleAnalysisError(ArticleProcessingError):
    """Exception raised when article analysis fails.
    
    This exception is raised when there are issues processing or analyzing
    the article content, such as AI processing errors or invalid content format.
    """
    pass

# Configuration
class Settings(BaseSettings):
    openai_api_key: str = "test-key" if os.getenv("TESTING") else os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4"
    request_timeout: int = 30
    max_content_length: int = 100000
    allowed_domains: List[str] = [
        "nejm.org",
        "thelancet.com",
        "jamanetwork.com",
        "bmj.com",
        "mayoclinic.org",
        "health.harvard.edu"
    ]

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()

# Models
class ArticleRequest(BaseModel):
    url: Optional[str] = None
    text: Optional[str] = None

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not validators.url(v):
            raise ValueError("Invalid URL format")
        
        settings = get_settings()
        
        domain = v.split('/')[2] if len(v.split('/')) > 2 else ""
        if not any(allowed in domain for allowed in settings.allowed_domains):
            raise ValueError(f"Domain not allowed. Allowed domains: {', '.join(settings.allowed_domains)}")
        
        return v

    @model_validator(mode='before')
    @classmethod
    def check_url_or_text(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        url = values.get('url')
        text = values.get('text')
        if not url and not text:
            raise ValueError("Either url or text must be provided")
        if url and text:
            raise ValueError("Only one of url or text should be provided")
        
        if text and len(text) > get_settings().max_content_length:
            raise ValueError(f"Text content exceeds maximum length of {get_settings().max_content_length} characters")
        
        return values

# Services
class ArticleService:
    def __init__(self, settings: Settings = Depends(get_settings)) -> None:
        self.settings = settings
        openai.api_key = settings.openai_api_key
        timeout = aiohttp.ClientTimeout(total=settings.request_timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)

    async def fetch_article(self, url: str) -> str:
        try:
            async with self.session.get(url) as response:
                if response.status == 404:
                    raise ArticleFetchError("Article not found")
                response.raise_for_status()
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                text = soup.get_text()
                if not text.strip():
                    raise ArticleFetchError("No content found in article")
                return text
        except aiohttp.ClientError as e:
            raise ArticleFetchError(f"Error fetching article: {str(e)}")
        except Exception as e:
            raise ArticleFetchError(f"Unexpected error fetching article: {str(e)}")

    async def process_article_text(self, text: str) -> Dict[str, str]:
        try:
            tasks = [
                self._generate_summary(text),
                self._extract_terminology(text),
                self._assess_quality(text)
            ]
            summary, terminology, quality_assessment = await asyncio.gather(*tasks)
            
            return {
                "summary": summary,
                "terminology": terminology,
                "quality_assessment": quality_assessment
            }
        except Exception as e:
            raise ArticleAnalysisError(f"Error processing article text: {str(e)}")

    async def _generate_summary(self, text: str) -> str:
        completion: dict = await openai.ChatCompletion.acreate(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": "You are a medical content summarizer."},
                {"role": "user", "content": f"Summarize this medical article:\n\n{text}"}
            ]
        )
        return completion['choices'][0]['message']['content']

    async def _extract_terminology(self, text: str) -> str:
        completion = await openai.ChatCompletion.acreate(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": "Extract and explain medical terminology."},
                {"role": "user", "content": f"Extract and explain key medical terms from:\n\n{text}"}
            ]
        )
        return completion.choices[0].message.content

    async def _assess_quality(self, text: str) -> str:
        completion = await openai.ChatCompletion.acreate(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": "Assess medical study quality and methodology."},
                {"role": "user", "content": f"Assess the quality and methodology of this study:\n\n{text}"}
            ]
        )
        return completion.choices[0].message.content

    async def close(self):
        await self.session.close()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.article_service = ArticleService(get_settings())
    yield
    # Shutdown
    await app.state.article_service.close()

app = FastAPI(
    title="Health Article MCP",
    description="Medical Content Processing API for health articles",
    version="1.0.0",
    lifespan=lifespan
)

@app.post("/workflow/process")
async def process_workflow(
    request: Request,
    article_request: ArticleRequest,
    settings: Settings = Depends(get_settings)
):
    request_id = str(uuid.uuid4())
    logger.info(f"Processing request {request_id}")
    
    try:
        # Get content from URL or use provided text
        if article_request.url:
            content = await app.state.article_service.fetch_article(article_request.url)
        else:
            content = article_request.text

        if not content:
            raise HTTPException(status_code=400, detail="Empty article content")

        # Process the article
        result = await app.state.article_service.process_article_text(content)
        logger.info(f"Successfully processed request {request_id}")
        return result

    except ArticleFetchError as e:
        logger.error(f"Article fetch error for request {request_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except ArticleAnalysisError as e:
        logger.error(f"Article analysis error for request {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except ValueError as e:
        logger.error(f"Validation error for request {request_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error for request {request_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)