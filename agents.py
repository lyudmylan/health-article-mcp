import logging
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from openai import AsyncOpenAI
from error_handlers import ArticleFetchError, RetryableError
import aiohttp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fetch_article(url: str) -> str:
    """
    Fetch article content from URL.
    
    Args:
        url: URL of the article to fetch
        
    Returns:
        str: Article text content
        
    Raises:
        ArticleFetchError: If article cannot be fetched
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                response.raise_for_status()
                html = await response.text()
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'header', 'footer']):
                    element.decompose()
                
                # Get main content
                article = soup.find('article') or soup.find('main') or soup.find('body')
                if not article:
                    raise ArticleFetchError("Could not find article content")
                    
                return article.get_text(separator='\n', strip=True)
                
    except aiohttp.ClientError as e:
        raise ArticleFetchError(f"Failed to fetch article: {str(e)}")

async def summarize_text(text: str, client: AsyncOpenAI) -> str:
    """
    Generate a concise summary of the article text.
    
    Args:
        text: Article text to summarize
        client: OpenAI client instance
        
    Returns:
        str: Generated summary
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a medical research assistant. Summarize the following medical article in a clear, concise way that maintains accuracy and key findings."},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content
        
    except Exception as e:
        raise RetryableError(f"Failed to generate summary: {str(e)}")

async def explain_terminology(text: str, client: AsyncOpenAI) -> Dict[str, str]:
    """
    Extract and explain medical terminology from the text.
    
    Args:
        text: Article text to analyze
        client: OpenAI client instance
        
    Returns:
        Dict[str, str]: Dictionary of terms and their explanations
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a medical terminology expert. Extract medical terms from the text and provide clear, layperson-friendly explanations. Return the response as a JSON object with terms as keys and explanations as values."},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=1000,
            response_format={ "type": "json_object" }
        )
        return response.choices[0].message.content
        
    except Exception as e:
        raise RetryableError(f"Failed to explain terminology: {str(e)}")

async def assess_study_quality(text: str, client: AsyncOpenAI) -> Dict:
    """
    Assess the quality of the medical study.
    
    Args:
        text: Article text to analyze
        client: OpenAI client instance
        
    Returns:
        Dict: Quality assessment metrics
    """
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a medical research methodology expert. Assess the quality of the study based on its design, sample size, statistical methods, potential biases, and limitations. Return the assessment as a JSON object with standardized metrics."},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=1000,
            response_format={ "type": "json_object" }
        )
        return response.choices[0].message.content
        
    except Exception as e:
        raise RetryableError(f"Failed to assess study quality: {str(e)}") 