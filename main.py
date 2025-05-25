import json
import os
import time
from urllib.parse import urljoin
import logging
from typing import List
from pydantic import BaseModel, ValidationError
from bs4 import BeautifulSoup
import litellm
import re
from playwright.sync_api import sync_playwright


# Configure LiteLLM (you can set the environment variable or use directly)
litellm.api_key = "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"  # Replace with your API key

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WebCrawler")


# ----------------------------
# Step 1: Define your Pydantic model
# ----------------------------
class BlogPost(BaseModel):
    title: str
    description: str
    price: str
    image_link: str
    article_link: str


# ----------------------------
# Step 2: Fetch HTML content
# ----------------------------
def fetch_html(url: str, page_url: str = "") -> str:
    try:
        # If page_url is a relative URL, join it with the base URL
        full_url = urljoin(url, page_url) if page_url else url
        
        logger.info(f"Playwright fetching: {full_url}")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # Block all non-document requests (scripts, images, etc.)
            page.route(
                "**/*",
                lambda route, request: (
                    route.abort()
                    if request.resource_type != "document"
                    else route.continue_()
                ),
            )
            
            # Go to page and wait for DOMContentLoaded (not full load)
            page.goto(full_url, wait_until="networkidle", timeout=0)

            html = page.content()
            browser.close()
            return html
    except Exception as e:
        logger.error(f"Playwright failed to fetch {url}: {e}")
        return ""

def split_section_into_chunks(section: str, max_chunk_size: int = 2000) -> list:
    """
    Splits the section into smaller chunks to fit within LLM's token limit.
    
    Args:
        section (str): The HTML section to split.
        max_chunk_size (int): The maximum size (in characters) for each chunk.
    
    Returns:
        list: A list of smaller chunks.
    """
    # Split the section into paragraphs or logical chunks (based on your content).
    # Here we use simple splitting by paragraphs or sentences to keep the logic natural.
    paragraphs = re.split(r'(<p.*?>.*?</p>)', section)  # Split by HTML paragraphs (or other tag if needed)
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk + paragraph) <= max_chunk_size:
            current_chunk += paragraph
        else:
            chunks.append(current_chunk)
            current_chunk = paragraph  # Start a new chunk with this paragraph
    
    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


# ----------------------------
# Step 3: Extract content using selector
# ----------------------------
def extract_section(html: str, selector: str) -> str:
    try:
        soup = BeautifulSoup(html, "html.parser")
        section = soup.select_one(selector)
        return str(section) if section else ""
    except Exception as e:
        logger.error(f"Error extracting section with selector {selector}: {e}")
        return ""


# ----------------------------
# Step 4: Detect next page link
# ----------------------------
def get_next_page_url(html: str, next_page_selector: str) -> str:
    """Extract the next page URL using a selector for the 'next' page link."""
    try:
        soup = BeautifulSoup(html, "html.parser")
        next_page_link = soup.select_one(next_page_selector)
        if next_page_link and next_page_link.get("href"):
            return next_page_link["href"]
        return ""
    except Exception as e:
        logger.error(f"Error extracting next page URL: {e}")
        return ""


# ----------------------------
# Step 5: Use LLM to extract structured data
# ----------------------------
def extract_data_with_llm(content: str) -> List[BaseModel]:
    try:
        prompt = f"""
You're a smart parser. Extract structured data from the following text and return a list of items matching this Pydantic schema:
{BlogPost.model_json_schema()}

Content:
\"\"\" 
{content} 
\"\"\" 
Return ONLY the list of items in JSON format inside triple backticks as a valid JSON array.
"""

        response = litellm.completion(
            model="groq/deepseek-r1-distill-llama-70b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        raw_text = response["choices"][0]["message"]["content"]
        logger.debug(f"Raw LLM output:\n{raw_text}")

        match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
        if not match:
            raise ValueError("No JSON block found in LLM response")

        json_str = match.group(1)
        data = json.loads(json_str)

        # Ensure data is in the expected format (list of dictionaries)
        if not isinstance(data, list):
            raise ValueError(f"Expected a list of items, but got {type(data)}")

        # Create instances of the dynamically generated model
        return [BlogPost(**item) for item in data]

    except (ValidationError, json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error(f"Error parsing or validating LLM output: {e}")
        return []

    except litellm.exceptions.RateLimitError as e:
        # Handle rate limit exceeded error
        error_message = e.args[0]  # The message from the error contains the wait time information
        wait_time = float(re.search(r"try again in (\d+\.\d+)s", error_message).group(1)) + 1  # Add 1 second buffer
        
        logger.warning(f"Rate limit reached, waiting for {wait_time} seconds.")
        time.sleep(wait_time)  # Wait for the rate limit to reset
        
        # Retry the request after waiting
        return extract_data_with_llm(content)  # Retry the function call recursively


# ----------------------------
# Step 6: Main orchestrator
# ----------------------------
def crawl_and_extract(websites: List[dict]):
    results = []
    for site in websites:
        url = site.get("url")
        selector = site.get("selector")
        output_file = site.get("output_file")
        next_page_selector = site.get("next_page_selector")
        if not url or not selector:
            logger.warning("Skipping site with missing URL or selector.")
            continue

        page_number = 1  # Start with the first page
        while True:
            logger.info(f"Scraping page {page_number} of {url}")
            
            # Pass the correct page URL for the current page
            page_url = f"?page={page_number}"  # Adjust this based on how pagination works in your case
            html = fetch_html(url, page_url)
            
            if not html:
                logger.warning(f"Failed to fetch HTML for page {page_number}")
                break

            # Example usage in your code:
            section = extract_section(html, selector)
            if not section:
                logger.warning(f"Section not found on page {page_number}")
            else:
                # Split the section into smaller chunks
                chunks = split_section_into_chunks(section, max_chunk_size=1000)  # Adjust max_chunk_size as needed
                
                for chunk in chunks:
                    extracted = extract_data_with_llm(chunk)
                    if extracted:
                        logger.info(f"Extracted {len(extracted)} items from page {page_number}")
                        results.extend([item.model_dump() for item in extracted])  # Using model_dump() for Pydantic V2
                    else:
                        logger.warning(f"No data extracted from chunk on page {page_number}")

            # Check if there's a next page
            next_page_url = get_next_page_url(html, next_page_selector)
            if not next_page_url:
                logger.info("No more pages to scrape.")
                break

            page_number += 1

    if results:
        try:
            # Ensure the directory exists
            output_dir = os.path.dirname(output_file)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved output to {output_file}")
        except Exception as e:
            logger.error(f"Failed to write output: {e}")
    else:
        logger.info("No valid data to save.")


# ----------------------------
# Step 7: Example usage
# ----------------------------
if __name__ == "__main__":
    websites_to_scrape = [
        {
            "output_file": "data/theknot.json",
            "url": "https://www.theknot.com/marketplace/wedding-photographers-atlanta-ga",
            "selector": ".vertical-gutters--9318b",
            "next_page_selector": "a[rel=\"next\"]",  # Adjust this selector as needed
        },
        # Add more sites here
    ]

    crawl_and_extract(websites=websites_to_scrape)
