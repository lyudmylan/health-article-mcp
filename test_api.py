class MockArticleService:
    """Mock service for testing article processing functionality."""
    
    def __init__(self) -> None:
        self.mock_summary: str = "This is a mock summary"
        self.mock_terminology: str = "Term 1: Definition 1\nTerm 2: Definition 2"
        self.mock_quality: str = "Quality Score: 8/10. This is a high-quality study."

    async def fetch_article(self, url: str) -> str:
        """Mock article fetching."""
        if "not-found" in url:
            raise ArticleFetchError("Article not found")
        if "error" in url:
            raise ArticleProcessingError("Error processing article")
        return "Mock article content"

    async def process_article_text(self, text: str) -> Dict[str, str]:
        """Mock article processing."""
        if "error" in text.lower():
            raise ArticleAnalysisError("Error analyzing article")
        return {
            "summary": self.mock_summary,
            "terminology": self.mock_terminology,
            "quality_assessment": self.mock_quality
        } 