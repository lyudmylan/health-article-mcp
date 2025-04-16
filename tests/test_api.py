import pytest
from fastapi.testclient import TestClient
from main import app, ArticleFetchError, ArticleProcessingError, ArticleAnalysisError

class MockArticleService:
    def __init__(self):
        self.mock_summary = "This is a mock summary"
        self.mock_terminology = "Term 1: Definition 1\nTerm 2: Definition 2"
        self.mock_quality = "Quality Score: 8/10. This is a high-quality study."

    async def fetch_article(self, url: str) -> str:
        if "not-found" in url:
            raise ArticleFetchError("Article not found")
        if "error" in url:
            raise ArticleProcessingError("Error processing article")
        return "Mock article content"

    async def process_article_text(self, text: str) -> dict:
        if "error" in text.lower():
            raise ArticleAnalysisError("Error analyzing article")
        return {
            "summary": self.mock_summary,
            "terminology": self.mock_terminology,
            "quality_assessment": self.mock_quality
        }

    async def close(self):
        pass

@pytest.fixture
def mock_article_service():
    return MockArticleService()

@pytest.fixture
def test_client(mock_article_service):
    app.state.article_service = mock_article_service
    return TestClient(app)

def test_process_workflow_valid_url(test_client):
    response = test_client.post(
        "/workflow/process",
        json={"url": "https://www.nejm.org/valid-article"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "terminology" in data
    assert "quality_assessment" in data

def test_process_workflow_invalid_url(test_client):
    response = test_client.post(
        "/workflow/process",
        json={"url": "not-a-url"}
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("Invalid URL format" in error["msg"] for error in data["detail"])

def test_process_workflow_not_found(test_client):
    response = test_client.post(
        "/workflow/process",
        json={"url": "https://www.nejm.org/not-found-article"}
    )
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "Article not found" in data["detail"]

def test_process_workflow_server_error(test_client):
    response = test_client.post(
        "/workflow/process",
        json={"url": "https://www.nejm.org/error-article"}
    )
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Internal server error" in data["detail"]

def test_process_workflow_with_text(test_client):
    response = test_client.post(
        "/workflow/process",
        json={"text": "Sample medical article text"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "terminology" in data
    assert "quality_assessment" in data

def test_process_workflow_no_content(test_client):
    response = test_client.post(
        "/workflow/process",
        json={}
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("Either url or text must be provided" in error["msg"] for error in data["detail"])

def test_process_workflow_both_url_and_text(test_client):
    response = test_client.post(
        "/workflow/process",
        json={"url": "https://www.nejm.org/article", "text": "Sample text"}
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("Only one of url or text should be provided" in error["msg"] for error in data["detail"])

def test_process_workflow_disallowed_domain(test_client):
    response = test_client.post(
        "/workflow/process",
        json={"url": "https://disallowed-domain.com/article"}
    )
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("Domain not allowed" in error["msg"] and "Allowed domains:" in error["msg"] for error in data["detail"])