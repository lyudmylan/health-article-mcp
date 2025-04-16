import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from main import app
from typing import Dict

class MockResponse:
    def __init__(self, content):
        self.choices = [MagicMock(message=MagicMock(content=content))]

def get_mock_summary(text):
    """Generate consistent mock summaries based on input text"""
    if "exercise" in text.lower() and "heart disease" in text.lower():
        return "Regular exercise (30 minutes daily) can reduce cardiovascular events by 50% across all age groups."
    elif "trial" in text.lower() and "drug" in text.lower():
        return "Clinical trial shows new drug reduces symptoms by 60% vs placebo (p<0.001), with minimal side effects (5% GI discomfort)."
    elif "cdc" in text.lower() and "covid" in text.lower():
        return "CDC updates COVID-19 guidelines, emphasizing ventilation and mask use in high-risk settings based on airborne transmission research."
    elif "blood pressure" in text.lower():
        return "Recommendations for healthy blood pressure: reduce salt, exercise regularly, manage stress. These lifestyle changes may replace medication in mild hypertension cases."
    else:
        return "Test article summary"

@pytest.fixture
def mock_openai():
    """Mock OpenAI client with content-aware responses"""
    mock = MagicMock()
    
    def mock_create(**kwargs):
        messages = kwargs.get('messages', [])
        user_message = next((m for m in messages if m['role'] == 'user'), None)
        if user_message:
            return MockResponse(get_mock_summary(user_message['content']))
        return MockResponse("Test article summary")
    
    mock.chat.completions.create = mock_create
    return mock

@pytest.fixture
def client(mock_openai):
    """Test client fixture with mocked OpenAI"""
    # Store the original client
    original_client = getattr(app.state, "openai_client", None)
    
    # Set the mock client
    app.state.openai_client = mock_openai
    
    # Create and return the test client
    test_client = TestClient(app)
    
    # Yield the client for the test
    yield test_client
    
    # Restore the original client after the test
    if original_client:
        app.state.openai_client = original_client
    else:
        delattr(app.state, "openai_client")

@pytest.fixture
def test_urls() -> Dict[str, str]:
    """Dictionary of real test URLs for different types of medical content"""
    return {
        "research": "https://www.nejm.org/doi/full/10.1056/NEJMoa2118542",  # NEJM COVID study
        "news": "https://www.health.harvard.edu/blog/intermittent-fasting-surprising-update-2018062914156",
        "guidelines": "https://www.cdc.gov/coronavirus/2019-ncov/your-health/isolation.html",  # CDC guidelines
        "medical_advice": "https://www.mayoclinic.org/diseases-conditions/high-blood-pressure/in-depth/high-blood-pressure/art-20046974",  # Mayo Clinic BP advice
        "clinical_trial": "https://clinicaltrials.gov/study/NCT04505722",  # Moderna COVID vaccine trial
        "not_found": "https://www.health.harvard.edu/blog/article-does-not-exist-404"  # Non-existent article for 404 testing
    }

@pytest.fixture
def test_url(test_urls):
    """Legacy fixture for backward compatibility"""
    return test_urls["news"] 