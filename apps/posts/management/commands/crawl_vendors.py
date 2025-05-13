from django.core.management.base import BaseCommand
from django.conf import settings
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from jsonschema import ValidationError
from playwright.sync_api import sync_playwright
import litellm
import re
import json
import time
from typing import List

from apps.posts.models import Vendor
from apps.posts.schemas import VendorData


class Command(BaseCommand):
    help = 'Crawl wedding vendor websites and save to database'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.websites = [
            {
                "url": "https://www.theknot.com/marketplace/wedding-photographers-atlanta-ga",
                "selector": ".vertical-gutters--9318b",
                "next_page_selector": "a[rel='next']",
            }
        ]
        litellm.api_key = settings.LITELLM_API_KEY

    def handle(self, *args, **options):
        """Main entry point for the command"""
        self.stdout.write("Starting vendor crawl...")

        try:
            for site in self.websites:
                self.process_site(site)

            self.stdout.write(self.style.SUCCESS('Successfully crawled all vendors'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during crawling: {str(e)}'))

    def process_site(self, site):
        """Process a single website configuration"""
        url = site["url"]
        selector = site["selector"]
        next_selector = site["next_page_selector"]

        self.stdout.write(f"Processing site: {url}")

        page_num = 1
        while True:
            self.stdout.write(f"  Page {page_num}...")

            html = self.fetch_html(url, f"?page={page_num}")
            if not html:
                self.stdout.write(self.style.WARNING("  No HTML content received"))
                break

            section = self.extract_section(html, selector)
            if not section:
                self.stdout.write(self.style.WARNING("  No section found"))
                break

            self.process_section(section)

            if not self.has_next_page(html, next_selector):
                break

            page_num += 1
            time.sleep(2)  # Respectful crawling delay

    def fetch_html(self, url, page_url):
        """Fetch HTML content using Playwright"""
        try:
            full_url = urljoin(url, page_url)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                page = context.new_page()

                page.route("**/*", lambda route, request: (
                    route.abort() if request.resource_type != "document" else route.continue_()
                ))

                page.goto(full_url, wait_until="domcontentloaded", timeout=60000)
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Fetch error: {str(e)}"))
            return None

    def extract_section(self, html, selector):
        """Extract HTML section using CSS selector"""
        try:
            soup = BeautifulSoup(html, "html.parser")
            return str(soup.select_one(selector)) or ""
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Extraction error: {str(e)}"))
            return ""

    def process_section(self, section):
        """Process a content section"""
        chunks = self.split_into_chunks(section)
        for chunk in chunks:
            vendors = self.extract_vendors(chunk)
            self.save_vendors(vendors)

    @staticmethod
    def split_into_chunks(section, max_size=2000):
        """Split HTML section into manageable chunks"""
        return re.split(r'(<p.*?>.*?</p>)', section)[::2]  # Split on paragraphs

    def extract_vendors(self, content):
        """Extract vendors using LLM"""
        try:
            prompt = (f"Extract vendor data matching:\n{self.vendor_schema()}\n\nContent:\n\"\"\"{content}\"\"\"\n\n"
                      f"Return ONLY a JSON array in triple backticks.")
            response = litellm.completion(
                model="groq/deepseek-r1-distill-llama-70b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )

            return self.parse_llm_response(response.choices[0].message.content)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  LLM error: {str(e)}"))
            return []

    def vendor_schema(self):
        """Return JSON schema for vendor validation"""
        return VendorData.model_json_schema()

    def parse_llm_response(self, raw_text):
        """Parse LLM response into Pydantic models"""
        try:
            json_match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found")

            return [VendorData(**item) for item in json.loads(json_match.group(1))]
        except (ValidationError, json.JSONDecodeError) as e:
            self.stdout.write(self.style.ERROR(f"  Parsing error: {str(e)}"))
            return []

    def save_vendors(self, vendors):
        """Save vendors to database"""
        for vendor in vendors:
            Vendor.objects.update_or_create(
                article_link=vendor.article_link,
                defaults={
                    'title': vendor.title[:255],
                    'description': vendor.description,
                    'price': vendor.price[:100],
                    'image_link': vendor.image_link
                }
            )
            self.stdout.write(f"  Saved/updated: {vendor.title[:30]}...")

    def has_next_page(self, html, selector):
        """Check for next page availability"""
        try:
            soup = BeautifulSoup(html, "html.parser")
            return bool(soup.select_one(selector))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Next page check error: {str(e)}"))
            return False
