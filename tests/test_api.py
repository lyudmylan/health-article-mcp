import pytest
from fastapi.testclient import TestClient
import json
from unittest.mock import patch
from agents import ArticleFetchError
from main import fetch_article, summarize_text
from uuid import uuid4

def test_process_workflow_valid_url(client, test_url):
    """Test processing workflow with a valid URL"""
    with patch('main.fetch_article') as mock_fetch:
        mock_fetch.return_value = "Test article content"
        response = client.post(
            "/workflow/process",
            json={
                "message_id": str(uuid4()),
                "conversation_id": str(uuid4()),
                "sender_agent": "UserAgent",
                "recipient_agent": "ArticleFetcherAgent",
                "timestamp": "2024-03-15T10:00:00Z",
                "payload_type": "url",
                "payload": {"url": test_url}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "summary" in data["data"]

def test_process_workflow_invalid_url(client):
    """Test processing workflow with an invalid URL"""
    response = client.post(
        "/workflow/process",
        json={
            "message_id": str(uuid4()),
            "conversation_id": str(uuid4()),
            "sender_agent": "UserAgent",
            "recipient_agent": "ArticleFetcherAgent",
            "timestamp": "2024-03-15T10:00:00Z",
            "payload_type": "url",
            "payload": {"url": "invalid_url"}
        }
    )
    assert response.status_code == 400

def test_process_workflow_404_url(client, test_urls):
    """Test processing workflow with a URL that returns 404"""
    with patch('main.fetch_article') as mock_fetch:
        mock_fetch.side_effect = ArticleFetchError("Article not found: 404 Client Error: Not Found for url: " + test_urls["not_found"])
        response = client.post(
            "/workflow/process",
            json={
                "message_id": str(uuid4()),
                "conversation_id": str(uuid4()),
                "sender_agent": "UserAgent",
                "recipient_agent": "ArticleFetcherAgent",
                "timestamp": "2024-03-15T10:00:00Z",
                "payload_type": "url",
                "payload": {"url": test_urls["not_found"]}
            }
        )
        assert response.status_code == 400
        error_data = response.json()
        assert "Article not found" in error_data["detail"]
        assert "404" in error_data["detail"]

def test_mocked_workflow(client, test_urls):
    """Test the entire workflow with mocked functions"""
    with patch('main.fetch_article') as mock_fetch:
        mock_fetch.return_value = "Test article content"
        response = client.post(
            "/workflow/process",
            json={
                "message_id": str(uuid4()),
                "conversation_id": str(uuid4()),
                "sender_agent": "UserAgent",
                "recipient_agent": "ArticleFetcherAgent",
                "timestamp": "2024-03-15T10:00:00Z",
                "payload_type": "url",
                "payload": {"url": test_urls["clinical_trial"]}
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "summary" in data["data"]
        assert data["data"]["summary"] == "Test article summary"

def test_invalid_payload_type(client, test_urls):
    """Test invalid payload type"""
    response = client.post(
        "/workflow/process",
        json={
            "message_id": str(uuid4()),
            "conversation_id": str(uuid4()),
            "sender_agent": "UserAgent",
            "recipient_agent": "ArticleFetcherAgent",
            "timestamp": "2024-03-15T10:00:00Z",
            "payload_type": "invalid",
            "payload": {"url": test_urls["news"]}
        }
    )
    assert response.status_code == 400

def test_invalid_json(client):
    """Test invalid JSON request"""
    response = client.post("/workflow/process", json={})
    assert response.status_code == 422

def test_summarizer_consistency(client, test_urls):
    """Test that summarizer produces consistent output for the same input"""
    test_article = """
    A new study shows that regular exercise can significantly reduce the risk of heart disease.
    The research, conducted over 5 years with 10,000 participants, demonstrated that
    30 minutes of daily moderate exercise led to a 50% reduction in cardiovascular events.
    The study also found that the benefits were consistent across all age groups.
    """
    
    with patch('main.fetch_article') as mock_fetch:
        mock_fetch.return_value = test_article
        
        # First request with Harvard URL
        response1 = client.post(
            "/workflow/process",
            json={
                "message_id": str(uuid4()),
                "conversation_id": str(uuid4()),
                "sender_agent": "UserAgent",
                "recipient_agent": "ArticleFetcherAgent",
                "timestamp": "2024-03-15T10:00:00Z",
                "payload_type": "url",
                "payload": {"url": test_urls["news"]}
            }
        )
        
        # Second request with same content but different URL
        response2 = client.post(
            "/workflow/process",
            json={
                "message_id": str(uuid4()),
                "conversation_id": str(uuid4()),
                "sender_agent": "UserAgent",
                "recipient_agent": "ArticleFetcherAgent",
                "timestamp": "2024-03-15T10:00:00Z",
                "payload_type": "url",
                "payload": {"url": test_urls["research"]}
            }
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        summary1 = response1.json()["data"]["summary"]
        summary2 = response2.json()["data"]["summary"]
        
        # Check that summaries are identical for same input
        assert summary1 == summary2
        # Check that summary contains key information
        assert "exercise" in summary1.lower()
        assert "heart disease" in summary1.lower() or "cardiovascular" in summary1.lower()

def test_summarizer_different_content_types(client, test_urls):
    """Test summarizer handles different types of medical content appropriately"""
    test_articles = {
        "research_study": """
        A randomized controlled trial of 500 patients showed that the new drug reduced symptoms
        by 60% compared to placebo. The p-value was <0.001, indicating statistical significance.
        Side effects were minimal, with only 5% reporting mild gastrointestinal discomfort.
        """,
        "health_news": """
        The CDC has updated its guidelines for COVID-19 prevention. The new recommendations
        emphasize the importance of proper ventilation and mask-wearing in high-risk settings.
        These changes reflect recent research on airborne transmission.
        """,
        "medical_advice": """
        To maintain healthy blood pressure, doctors recommend reducing salt intake,
        exercising regularly, and managing stress. These lifestyle changes can be as
        effective as medication for some patients with mild hypertension.
        """
    }
    
    url_mapping = {
        "research_study": test_urls["research"],
        "health_news": test_urls["guidelines"],
        "medical_advice": test_urls["medical_advice"]
    }
    
    summaries = {}
    for content_type, article in test_articles.items():
        with patch('main.fetch_article') as mock_fetch:
            mock_fetch.return_value = article
            response = client.post(
                "/workflow/process",
                json={
                    "message_id": str(uuid4()),
                    "conversation_id": str(uuid4()),
                    "sender_agent": "UserAgent",
                    "recipient_agent": "ArticleFetcherAgent",
                    "timestamp": "2024-03-15T10:00:00Z",
                    "payload_type": "url",
                    "payload": {"url": url_mapping[content_type]}
                }
            )
            
            assert response.status_code == 200
            summary = response.json()["data"]["summary"]
            summaries[content_type] = summary
            
            # Check content-specific key elements
            if content_type == "research_study":
                assert any(term in summary.lower() for term in ["trial", "study", "patients", "results"])
            elif content_type == "health_news":
                assert any(term in summary.lower() for term in ["cdc", "guidelines", "recommendations"])
            elif content_type == "medical_advice":
                assert any(term in summary.lower() for term in ["recommend", "advice", "should", "can"]) 