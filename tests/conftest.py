import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import json
from typing import AsyncGenerator, Generator
from main import app, ArticleService, get_settings

@pytest_asyncio.fixture
async def mock_redis() -> AsyncMock:
    mock = AsyncMock()
    mock.zcount.return_value = 0  # Default: no requests made
    mock.get.return_value = None  # Default: no cache hit
    mock.zadd = AsyncMock()
    mock.set = AsyncMock()
    return mock

@pytest_asyncio.fixture
async def mock_openai() -> AsyncMock:
    mock = AsyncMock()
    mock.chat.completions.create.return_value.choices[0].message.content = "Mocked response"
    return mock

@pytest.fixture
def mock_article_service(mock_openai) -> ArticleService:
    service = MagicMock(spec=ArticleService)
    service.fetch_article = AsyncMock()
    service.process_article_text = AsyncMock()
    service.openai_client = mock_openai
    return service

@pytest.fixture
def test_client(mock_article_service) -> TestClient:
    app.state.article_service = mock_article_service
    return TestClient(app)

@pytest_asyncio.fixture
def test_article_content() -> str:
    return """
    Abstract
    Background: This is a test medical article abstract.
    Methods: We conducted a randomized controlled trial.
    Results: The treatment showed significant improvement.
    Conclusion: The study supports the efficacy of the treatment.
    """

# Test URLs for different scenarios
test_urls = {
    "valid": "https://www.nejm.org/valid-article",
    "invalid": "not-a-url",
    "cached": "https://www.nejm.org/cached-article",
    "error": "https://www.nejm.org/error-article",
    "not_found": "https://www.nejm.org/not-found"
} 