import json
import os
import time
from urllib.parse import urljoin
import logging
from typing import List
from pydantic import BaseModel, ValidationError
from bs4 import BeautifulSoup
import litellm
from dotenv import load_dotenv
import re
from playwright.sync_api import sync_playwright


# Load environment variables
load_dotenv()

# Configure LiteLLM with Groq
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
litellm.groq_key = GROQ_API_KEY

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebCrawler")


import requests
from bs4 import BeautifulSoup
from litellm import completion

class BlogPost(BaseModel):
    title: str
    description: str
    price: str
    image_link: str
    article_link: str

class HTMLProcessor:
    def __init__(self, model="groq/deepseek-r1-distill-llama-70b", max_chars=4000):
        self.model = model
        self.max_chars = max_chars

    def load_html_from_file(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def fetch_html_from_url(self, url):
        import requests
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text

    def extract_clean_text(self, html):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)

    def split_text(self, text):
        lines = text.splitlines()
        chunks, chunk = [], []
        for line in lines:
            if sum(len(l) for l in chunk) + len(line) < self.max_chars:
                chunk.append(line)
            else:
                chunks.append("\n".join(chunk))
                chunk = [line]
        if chunk:
            chunks.append("\n".join(chunk))
        return chunks

    def send_to_llm(self, chunks):
        results = []
        schema_str = json.dumps(BlogPost.model_json_schema(), indent=2).replace("{", "{{").replace("}", "}}")
        prompt_template = (
            "You're a smart parser. Extract only the main data from the HTML content. "
            "Content:\n\"\"\"\n{content}\n\"\"\"\n"
            "Return ONLY the main content in html format, and remove all other content, including related posts and ads. the returned content should not have any styles or classes or ids, or any kinds of data attributes."
        )

        for i, chunk in enumerate(chunks):
            print(f"--- Sending chunk {i + 1} ---")
            prompt = prompt_template.format(content=chunk)
            response = completion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            content = response['choices'][0]['message']['content']
            results.append(content)
        return results

from apps.posts.models import CrawledPost

def save_llm_response_to_crawled_post(url: str, parsed_content: str) -> bool:
    try:
        post = CrawledPost.objects.get(url=url)
        post.content = parsed_content
        post.is_processed = True
        post.save()
        return True
    except CrawledPost.DoesNotExist:
        print(f"[ERROR] CrawledPost not found for URL: {url}")
        return False
    
def crawl_and_extract(site_url: str):
    processor = HTMLProcessor()
    html = processor.fetch_html_from_url(site_url)

    text = processor.extract_clean_text(html)
    chunks = processor.split_text(text)
    results = processor.send_to_llm(chunks)

    for idx, res in enumerate(results):
        print(f"\n--- Response {idx + 1} ---\n{res}")

    save_llm_response_to_crawled_post(site_url, results)
    
    if not html:
        logger.warning(f"Failed to fetch HTML")
        return False

    return True
