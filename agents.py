import requests
from bs4 import BeautifulSoup
from typing import Optional
from openai import OpenAI

class ArticleFetchError(Exception):
    pass

def fetch_article(url: str) -> str:
    """
    Fetches and extracts the main content from a given URL.
    
    Args:
        url (str): The URL of the article to fetch
        
    Returns:
        str: The extracted main content of the article
        
    Raises:
        ArticleFetchError: If there's an error fetching or parsing the article
    """
    try:
        # Send request with headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'iframe']):
            element.decompose()
        
        # Extract main content (this is a simple implementation)
        # For production, you'd want to implement site-specific extractors
        main_content = ""
        
        # Try to find article content in common containers
        article = soup.find('article') or soup.find(class_=['article', 'post', 'content', 'main-content'])
        if article:
            main_content = article.get_text(separator='\n', strip=True)
        else:
            # Fallback to main tag or body
            main = soup.find('main') or soup.find('body')
            if main:
                main_content = main.get_text(separator='\n', strip=True)
        
        if not main_content:
            raise ArticleFetchError("Could not extract meaningful content from the page")
            
        return main_content.strip()
        
    except requests.RequestException as e:
        raise ArticleFetchError(f"Error fetching article: {str(e)}")
    except Exception as e:
        raise ArticleFetchError(f"Error processing article: {str(e)}")

def summarize_text(text: str, openai_client: OpenAI) -> str:
    """
    Generates a summary of the provided text using OpenAI's API.
    
    Args:
        text (str): The text to summarize
        openai_client (OpenAI): Initialized OpenAI client
        
    Returns:
        str: The generated summary
    """
    try:
        # Prepare the system message with specific instructions
        system_message = """You are a medical content summarizer. Your task is to:
1. Provide a concise summary of the key findings or main points
2. Focus on clinical relevance and practical implications
3. Maintain scientific accuracy while using clear language
4. Include any significant statistical findings or evidence strength
5. Note any major limitations mentioned

Format your response in a clear, structured way."""

        # Create the completion request
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",  # Using GPT-4 for better medical understanding
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Please summarize this medical article:\n\n{text}"}
            ],
            temperature=0.3,  # Lower temperature for more focused/consistent output
            max_tokens=1000   # Adjust based on desired summary length
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        raise Exception(f"Error generating summary: {str(e)}")

def explain_terminology(text: str, openai_client: OpenAI) -> dict:
    """
    Identifies and explains medical terminology from the provided text.
    
    Args:
        text (str): The text containing medical terms to explain
        openai_client (OpenAI): Initialized OpenAI client
        
    Returns:
        dict: A dictionary containing terms and their explanations
    """
    try:
        system_message = """You are a medical terminology expert. Your task is to:
1. Identify important medical terms, abbreviations, and concepts from the text
2. Provide clear, layperson-friendly explanations for each term
3. Focus on terms that are crucial for understanding the content
4. Include brief context for why each term is important
5. Organize terms alphabetically

Return the response as a JSON object where keys are medical terms and values are their explanations."""

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Please identify and explain medical terminology from this text:\n\n{text}"}
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={ "type": "json_object" }
        )
        
        return eval(response.choices[0].message.content.strip())
        
    except Exception as e:
        raise Exception(f"Error explaining terminology: {str(e)}")

def assess_study_quality(text: str, openai_client: OpenAI) -> dict:
    """
    Assesses the quality and reliability of the medical study or article.
    
    Args:
        text (str): The text of the study to assess
        openai_client (OpenAI): Initialized OpenAI client
        
    Returns:
        dict: A dictionary containing quality assessment metrics and explanations
    """
    try:
        system_message = """You are a medical research methodology expert. Your task is to assess the quality of the study by evaluating:
1. Study Design and Methodology
2. Sample Size and Population
3. Statistical Analysis and Significance
4. Potential Biases and Limitations
5. Funding Sources and Conflicts of Interest
6. Peer Review Status
7. Evidence Level (based on standard evidence hierarchies)

Return the assessment as a JSON object with the following structure:
{
    "study_design": {"rating": "1-5", "explanation": "..."},
    "sample_quality": {"rating": "1-5", "explanation": "..."},
    "statistical_rigor": {"rating": "1-5", "explanation": "..."},
    "bias_assessment": {"rating": "1-5", "explanation": "..."},
    "transparency": {"rating": "1-5", "explanation": "..."},
    "evidence_level": {"level": "I-V", "explanation": "..."},
    "overall_score": {"rating": "1-5", "explanation": "..."},
    "key_limitations": ["limitation1", "limitation2", "..."],
    "recommendations": ["recommendation1", "recommendation2", "..."]
}"""

        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Please assess the quality of this medical study:\n\n{text}"}
            ],
            temperature=0.3,
            max_tokens=2000,
            response_format={ "type": "json_object" }
        )
        
        return eval(response.choices[0].message.content.strip())
        
    except Exception as e:
        raise Exception(f"Error assessing study quality: {str(e)}") 