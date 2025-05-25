from django.db import models
from .models import SourceWebsite, CrawledPost, CrawlLog  # Import your models
import os
import re
import json
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from readability import Document
from django.utils import timezone
import litellm
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
# Load environment variables
load_dotenv()

# Configure LiteLLM with Groq
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
litellm.groq_key = GROQ_API_KEY

class BlogCrawler:
    def __init__(self, domain, max_pages=10, max_workers=5):
        self.domain = self.normalize_domain(domain)
        self.base_url = f"https://{self.domain}"
        self.max_pages = max_pages
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.blog_path = None
        self.post_url_pattern = None
        self.source_website, _ = SourceWebsite.objects.get_or_create(domain=self.domain)
        
    @staticmethod
    def normalize_domain(domain):
        """Normalize the domain to remove protocol and paths"""
        domain = domain.lower().strip()
        if domain.startswith(('http://', 'https://')):
            domain = domain.split('//')[1]
        domain = domain.split('/')[0]
        return domain
        
    def is_valid_url(self, url):
        """Check if URL belongs to the domain and is valid"""
        parsed = urlparse(url)
        if not parsed.netloc:
            return False
        if parsed.netloc != self.domain and not parsed.netloc.endswith(f".{self.domain}"):
            return False
        if not parsed.scheme in ('http', 'https'):
            return False
        return True
        
    def find_blog_section(self):
        """Use LLM to identify the blog path from homepage"""
        try:
            print(f" - Fetching homepage: {self.base_url}")
            response = self.session.get(self.base_url, timeout=10)
            response.raise_for_status()

            print(" - Analyzing links...")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all links
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            links = [urljoin(self.base_url, l) for l in links if self.is_valid_url(l)]
            
            if not links:
                print(" - No valid links found on homepage")
                return False
            
            print(f" - Found {len(links)} links, analyzing with LLM...")
            
            # Prepare prompt for LLM
            prompt = f"""Analyze these URLs from {self.domain} and identify which path is most likely the blog section.
            Return ONLY the path segment (like '/blog' or '/news') or 'None' if not clear.
            
            URLs:
            {links[:20]}  # Limit to first 20 to avoid token limits
            
            Most likely blog path:"""
            
            # Get LLM analysis using LiteLLM
            response = litellm.completion(
                model="groq/deepseek-r1-distill-llama-70b",
                messages=[{"content": prompt, "role": "user"}],
                max_tokens=50,
                temperature=0.1
            )
            
            blog_path = response.choices[0].message.content.strip()
            
            if blog_path.lower() == 'none' or not blog_path:
                # Fallback to common blog paths
                common_paths = ['/blog', '/news', '/articles', '/stories', '/journal']
                for path in common_paths:
                    test_url = urljoin(self.base_url, path)
                    try:
                        resp = self.session.head(test_url, timeout=5, allow_redirects=True)
                        if resp.status_code == 200:
                            blog_path = path
                            break
                    except:
                        continue
            
            if blog_path and blog_path != 'None':
                self.blog_path = blog_path
                self.source_website.blog_path = blog_path
                self.source_website.save()
                return True
            return False
            
        except Exception as e:
            print(f"Error finding blog section: {e}")
            return False
            
    def discover_pagination_pattern(self, blog_url):
        """Analyze pagination structure"""
        try:
            response = self.session.get(blog_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for common pagination elements
            pagination = soup.find_all(['a', 'div'], class_=re.compile(r'page|pagination|next|prev', re.I))
            page_links = []
            
            for elem in pagination:
                if elem.name == 'a' and elem.get('href'):
                    href = elem.get('href')
                    if self.is_valid_url(href):
                        page_links.append(href)
            
            # If we found pagination links, try to identify pattern
            if page_links:
                # Look for numeric patterns
                for link in page_links:
                    match = re.search(r'page=(\d+)', link) or re.search(r'/page/(\d+)', link)
                    if match:
                        return {
                            'type': 'query_param' if 'page=' in link else 'path',
                            'template': link.replace(match.group(1), '{page}')
                        }
            
            # If no clear pattern, assume infinite scroll or "load more"
            return None
            
        except Exception as e:
            print(f"Error discovering pagination: {e}")
            return None
            
    def extract_post_links(self, html):
        """Extract post links from a blog listing page"""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        # Common patterns for blog post links
        patterns = [
            {'tag': 'article', 'class': re.compile(r'post|article|blog', re.I)},
            {'tag': 'div', 'class': re.compile(r'post|article|blog', re.I)},
            {'tag': 'a', 'class': re.compile(r'post|article|blog', re.I)},
            {'tag': 'h2', 'class': re.compile(r'entry-title|post-title', re.I)},
        ]
        
        for pattern in patterns:
            elements = soup.find_all(pattern['tag'], class_=pattern.get('class'))
            for elem in elements:
                link = None
                if elem.name == 'a':
                    link = elem.get('href')
                else:
                    link_elem = elem.find('a')
                    if link_elem:
                        link = link_elem.get('href')
                
                if link and self.is_valid_url(link):
                    links.append(urljoin(self.base_url, link))
        
        # Deduplicate
        return list(set(links))
        
    def crawl_blog_listings(self):
        """Crawl through blog listing pages to find all posts"""
        if not self.blog_path:
            if not self.find_blog_section():
                CrawlLog.objects.create(
                    source=self.source_website,
                    status='error',
                    message='Could not identify blog section'
                )
                return []
        
        blog_url = urljoin(self.base_url, self.blog_path)
        pagination = self.discover_pagination_pattern(blog_url)
        all_posts = set()
        
        try:
            # First page
            response = self.session.get(blog_url, timeout=10)
            posts = self.extract_post_links(response.text)
            all_posts.update(posts)
            
            # Handle pagination if exists
            if pagination:
                for page in range(2, self.max_pages + 1):
                    try:
                        if pagination['type'] == 'query_param':
                            next_url = f"{blog_url}?{pagination['template'].format(page=page)}"
                        else:
                            next_url = pagination['template'].format(page=page)
                        
                        response = self.session.get(next_url, timeout=10)
                        new_posts = self.extract_post_links(response.text)
                        
                        if not new_posts or all(p in all_posts for p in new_posts):
                            break  # No new posts or reached end
                            
                        all_posts.update(new_posts)
                        
                    except Exception as e:
                        print(f"Error crawling page {page}: {e}")
                        break
            
            return list(all_posts)
            
        except Exception as e:
            print(f"Error crawling blog listings: {e}")
            return []
            
    def extract_post_content(self, url):
        """Extract main content from a blog post URL"""
        try:
            response = self.session.get(url, timeout=10)
            doc = Document(response.text)
            
            # Use readability to extract main content
            soup = BeautifulSoup(doc.summary(), 'html.parser')
            
            # Clean up content
            for element in soup(['script', 'style', 'nav', 'footer', 'iframe', 'aside']):
                element.decompose()
                
            content = soup.get_text('\n', strip=True)
            
            # Get title
            title = doc.title()
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'raw_html': response.text,
                'metadata': {
                    'language': 'en',  # Default, can be detected later
                    'word_count': len(content.split()),
                    'extracted_at': timezone.now().isoformat()
                }
            }
            
        except Exception as e:
            print(f"Error extracting content from {url}: {e}")
            return None
            
    def save_post(self, post_data):
        """Save extracted post to database"""
        try:
            post, created = CrawledPost.objects.get_or_create(
                url=post_data['url'],
                defaults={
                    'source': self.source_website,
                    'title': post_data['title'],
                    'content': post_data['content'],
                    'raw_html': post_data['raw_html'],
                    'metadata': post_data['metadata']
                }
            )
            return created
        except Exception as e:
            print(f"Error saving post {post_data['url']}: {e}")
            return False
            
    def crawl_site(self):
        """Main method to crawl a site and save posts"""
        start_time = time.time()
        print(f"\nStarting crawl for {self.domain}")
        
        # Step 1: Find blog posts
        print("1. Finding blog section...")
        post_urls = self.crawl_blog_listings()
        if not post_urls:
            print("ERROR: No posts found")
            CrawlLog.objects.create(
                source=self.source_website,
                status='error',
                message='No posts found',
                posts_found=0
            )
            return False
        
        print(f"2. Found {len(post_urls)} posts")
        # Step 2: Process posts in parallel
        saved_count = 0
        print("3. Processing posts...")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for url in post_urls:
                # Skip if already exists
                if CrawledPost.objects.filter(url=url).exists():
                    print(f" - Skipping existing post: {url}")
                    continue
                futures.append(executor.submit(self.extract_post_content, url))
            
            for future in as_completed(futures):
                result = future.result()
                if result and self.save_post(result):
                    saved_count += 1
                    print(f" + Saved post: {result['url']}")
        
        # Log results
        print(f"4. Crawling completed. Saved {saved_count} new posts")
        CrawlLog.objects.create(
            source=self.source_website,
            status='success',
            message=f'Crawled {len(post_urls)} posts, saved {saved_count} new ones',
            posts_found=len(post_urls)
        )
        
        print(f"Crawling completed in {time.time() - start_time:.2f} seconds")
        return True

def run_crawler(domain):
    """Run the crawler for a single domain"""
    crawler = BlogCrawler(domain)
    return crawler.crawl_site()

def batch_crawl(domains):
    """Run crawler for multiple domains"""
    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:  # Lower concurrency for multiple domains
        futures = {executor.submit(run_crawler, domain): domain for domain in domains}
        for future in as_completed(futures):
            domain = futures[future]
            try:
                results.append((domain, future.result()))
            except Exception as e:
                results.append((domain, str(e)))
    return results