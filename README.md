# AI Health Article Summarizer & Explainer

A FastAPI-based service that fetches, summarizes, and explains health articles using OpenAI's GPT models.

## Features

- Fetches health articles from various medical sources (Harvard Health, NEJM, CDC, Mayo Clinic, etc.)
- Summarizes articles using OpenAI's GPT models
- Handles different types of medical content (research papers, news, guidelines, medical advice)
- Provides consistent and reliable summaries
- Error handling for various scenarios (404s, invalid URLs, etc.)

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export OPENAI_API_KEY=your_api_key_here
```

## Running the Service

Start the FastAPI server:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## Testing

Run the tests using pytest:
```bash
TESTING=1 PYTHONPATH=. pytest tests/ -v
```

## API Endpoints

### POST /workflow/process

Process a health article URL and return a summary.

Request body:
```json
{
    "message_id": "uuid",
    "conversation_id": "uuid",
    "sender_agent": "UserAgent",
    "recipient_agent": "ArticleFetcherAgent",
    "timestamp": "2024-03-15T10:00:00Z",
    "payload_type": "url",
    "payload": {
        "url": "https://example.com/health-article"
    }
}
```

Response:
```json
{
    "success": true,
    "message": "Article processed successfully",
    "data": {
        "message_id": "uuid",
        "summary": "Article summary..."
    }
}
```

## Error Handling

The service handles various error cases:
- Invalid URLs
- Non-existent articles (404)
- Invalid request formats
- Server errors

Each error returns an appropriate HTTP status code and descriptive message. 