# AI Health Article Summarizer & Explainer

A FastAPI-based multi-agent system for processing and analyzing medical articles. The system fetches articles from URLs, generates summaries, explains medical terminology, and assesses study quality.

## Features

- **Article Fetching**: Extracts content from medical articles and research papers
- **Smart Summarization**: Generates concise, accurate summaries of medical content
- **Terminology Explanation**: Identifies and explains medical terms in layperson-friendly language
- **Quality Assessment**: Evaluates study quality based on methodology, sample size, statistical rigor, and more
- **Multi-Agent Architecture**: Coordinated processing through specialized agents
- **Error Handling & Retry Logic**: Robust error handling with exponential backoff retry mechanism
- **Rate Limiting**: Prevents API abuse with configurable rate limits
- **Response Caching**: Improves performance by caching responses
- **URL Validation**: Ensures only valid medical/academic URLs are processed

## Requirements

- Python 3.9+
- Redis server (for rate limiting and caching)
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/lyudmylan/health-article-mcp.git
cd health-article-mcp
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install and start Redis server:
```bash
# On macOS using Homebrew
brew install redis
brew services start redis

# On Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server
```

5. Set up environment variables:
```bash
export OPENAI_API_KEY='your-api-key-here'
export REDIS_URL='redis://localhost'  # Optional: default is localhost
export RATE_LIMIT_MAX_REQUESTS='60'   # Optional: requests per window
export RATE_LIMIT_WINDOW='60'         # Optional: window in seconds
export CACHE_TTL='3600'              # Optional: cache TTL in seconds
```

## Usage

1. Start the server:
```bash
python main.py
```

2. Send a POST request to process an article:
```bash
curl -X POST http://localhost:8000/workflow/process \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "123e4567-e89b-12d3-a456-426614174000",
    "conversation_id": "123e4567-e89b-12d3-a456-426614174001",
    "sender_agent": "UserAgent",
    "recipient_agent": "ArticleFetcherAgent",
    "payload_type": "url",
    "payload": {
      "url": "https://example.com/medical-article"
    }
  }'
```

## API Response

The API returns a JSON response with:
- Article summary
- Explained medical terminology
- Quality assessment metrics including:
  - Study design evaluation
  - Sample quality analysis
  - Statistical rigor assessment
  - Bias evaluation
  - Evidence level classification
  - Overall quality score
  - Key limitations and recommendations

Example response:
```json
{
  "success": true,
  "message": "Article processed successfully",
  "data": {
    "message_id": "123e4567-e89b-12d3-a456-426614174002",
    "summary": "Comprehensive summary of the article...",
    "terminology": {
      "Term 1": "Definition in simple language",
      "Term 2": "Another explanation..."
    },
    "quality_assessment": {
      "study_design": {
        "rating": "4",
        "explanation": "Well-designed cohort study"
      },
      "overall_score": {
        "rating": "4.2",
        "explanation": "High-quality study with minor limitations"
      },
      "key_limitations": [
        "Limited follow-up period",
        "Potential selection bias"
      ],
      "recommendations": [
        "Consider longer follow-up study",
        "Expand demographic diversity"
      ]
    }
  }
}
```

## Error Handling

The API includes comprehensive error handling:
- Input validation errors (400)
- Rate limiting errors (429)
- Network errors (503)
- Server errors (500)

Each error response includes a descriptive message and appropriate HTTP status code.

## Rate Limiting

The API implements rate limiting to prevent abuse:
- Default: 60 requests per minute per IP
- Configurable via environment variables
- Uses Redis for distributed rate limiting
- Returns 429 status code when limit exceeded

## Caching

Response caching improves performance:
- Default TTL: 1 hour
- Configurable via environment variables
- Uses Redis for distributed caching
- Automatic cache invalidation
- Cache keys based on request parameters

## URL Validation

The API validates URLs before processing:
- Ensures HTTPS/HTTP protocol
- Validates against whitelist of medical/academic domains
- Checks for malicious patterns
- Returns detailed validation errors

## Testing

Run the test suite:
```bash
TESTING=1 PYTHONPATH=. pytest tests/ -v
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 