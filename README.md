# AI Health Article Summarizer & Explainer

A FastAPI-based multi-agent system for processing and analyzing medical articles. The system fetches articles from URLs, generates summaries, explains medical terminology, and assesses study quality.

## Features

- **Article Fetching**: Extracts content from medical articles and research papers
- **Smart Summarization**: Generates concise, accurate summaries of medical content
- **Terminology Explanation**: Identifies and explains medical terms in layperson-friendly language
- **Quality Assessment**: Evaluates study quality based on methodology, sample size, statistical rigor, and more
- **Multi-Agent Architecture**: Coordinated processing through specialized agents

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

4. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
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