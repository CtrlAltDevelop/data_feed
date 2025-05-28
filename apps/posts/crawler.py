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

# this class has the responsibility of finding blog post links from a set of defined domains
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

    def find_blog_path(self):
        """Generic blog path detection using multiple strategies"""
        try:
            print(f"\nAttempting to find blog path on {self.domain}")

            # Strategy 1: Fetch homepage and analyze links
            print(" - Fetching homepage...")
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Collect all unique, valid links
            links = set()
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                    continue
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(self.base_url, href)
                if self.is_valid_url(href):
                    links.add(href)

            # Strategy 2: Look for common structural elements
            blog_candidates = set()
            for element in soup.find_all(['nav', 'header', 'main', 'section']):
                for a in element.find_all('a', href=True):
                    href = a['href'].strip()
                    if not href.startswith(('http://', 'https://')):
                        href = urljoin(self.base_url, href)
                    if self.is_valid_url(href):
                        blog_candidates.add(href)

            all_links = list(links.union(blog_candidates))

            if not all_links:
                print(" - No links found on homepage")
                return self.try_common_blog_paths()

            print(f" - Found {len(all_links)} potential links")

            # Strategy 3: Use LLM to analyze link patterns
            print(" - Analyzing link patterns with LLM...")
            prompt = f"""Analyze these URLs from {self.domain} and identify the most likely blog section path.
            Return ONLY the path segment (like '/blog') or 'None' if unclear. if you couldn't determine a path, return a path that you think is most likely content related since the user provided this domain they must be looking for something like a blog page even if you determine the the whole domain is a blog you should return a path that is most likely to be a blog page not the root.
            
            URLs:
            {sorted(all_links)}
            
            Blog path:"""

            response = litellm.completion(
                model="groq/deepseek-r1-distill-llama-70b",
                messages=[{"content": prompt, "role": "user"}],
                temperature=0
            )

            llm_response = response.choices[0].message.content.strip()
            print(f" - LLM response: {llm_response}")

            # Clean and validate LLM response
            blog_path = None
            if llm_response.lower() != 'none':
                # Extract first path-like segment from response
                match = re.search(r'(?:^|\s)(/\w[\w-]*)', llm_response)
                if match:
                    blog_path = match.group(1).rstrip('/')

            # Strategy 4: Verify the candidate path
            if blog_path:
                test_url = urljoin(self.base_url, blog_path.lstrip('/'))  # Clean leading slash
                print(f" - Testing candidate blog path: {test_url}")
                try:
                    resp = self.session.get(test_url, timeout=10)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, 'html.parser')

                        # Heuristic: Check if it resembles a blog
                        blog_like_elements = soup.select('article, div.post, div.blog-item, #blog, .blog, section.blog, #main')
                        if blog_like_elements:
                            self.blog_path = blog_path
                            self.source_website.blog_path = blog_path
                            self.source_website.save(update_fields=['blog_path'])
                            print(f" - Confirmed blog path: {blog_path}")
                            return True
                        else:
                            print(" - No blog-like elements found on the page.")
                    else:
                        print(f" - Received non-200 status code: {resp.status_code}")
                except requests.RequestException as e:
                    print(f" - Request failed: {e}")
                except Exception as e:
                    print(f" - Verification exception: {str(e)}")

            # Strategy 5: Fallback to common paths
            print(" - Trying common blog paths as fallback")
            return self.try_common_blog_paths()

        except Exception as e:
            print(f"Error in: {str(e)}")
            return False

    def try_common_blog_paths(self):
        """Systematically test common blog path patterns"""
        common_paths = [
            '/blog', '/news', '/latest', '/articles', '/stories',
            '/journal', '/updates', '/posts', '/writing',
            '/magazine', '/content', '/blog/posts'
        ]

        print(" - Testing common blog paths...")
        for path in common_paths:
            test_url = urljoin(self.base_url, path)
            try:
                print(f"   - Trying {path}...", end=' ')
                resp = self.session.get(test_url, timeout=8)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    # Verify page structure looks like a blog
                    if (soup.find('article') or 
                        soup.find(class_=re.compile('post|article|blog', re.I)) or
                        len(soup.find_all('a', href=re.compile(r'/blog/|/post/|/article/'))) >= 3):
                        self.blog_path = path
                        self.source_website.blog_path = path
                        self.source_website.save()
                        print("SUCCESS")
                        return True
                    print("not a blog")
                else:
                    print(f"status {resp.status_code}")
            except Exception as e:
                print(f"error: {str(e)}")
                continue

        print(" - No blog path found through common patterns")
        return False

    def discover_pagination_pattern(self, blog_url):
        """Pagination detection focusing on blog-related URLs"""
        if self.source_website.pagination_pattern:
            return json.loads(f"\"{self.source_website.pagination_pattern}\"")

        print(" - Detecting pagination pattern...")
        try:
            response = self.session.get(blog_url, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Normalize blog URL for comparison
            normalized_blog_url = blog_url.rstrip('/') + '/'

            # Collect potential pagination links using multiple strategies
            potential_links = set()

            # Strategy 1: Links with pagination-related attributes
            for a in soup.find_all('a', href=True):
                href = a.get('href')
                if not href:
                    continue

                full_url = urljoin(blog_url, href)

                # Check URL characteristics
                url_matches = (
                    self.is_valid_url(full_url) and
                    any([
                        # Case 1: URL contains pagination terms
                        re.search(r'page|pagination|pager|[\?\&]page=|/page/|/p/', href, re.I),
                        # Case 2: Link text suggests pagination
                        a.text and re.search(r'^\d+$|next|prev|older|newer', a.text.strip(), re.I),
                        # Case 3: URL follows blog structure with numbers
                        (full_url.startswith(normalized_blog_url) and re.search(r'\d', href))
                    ])
                )

                if url_matches:
                    potential_links.add(full_url)

            # Strategy 2: Pagination containers
            pagination_containers = soup.find_all(['nav', 'div', 'ul'], 
                                            class_=re.compile(r'pagination|pager|pages', re.I))
            for container in pagination_containers:
                for a in container.find_all('a', href=True):
                    full_url = urljoin(blog_url, a.get('href'))
                    if self.is_valid_url(full_url):
                        potential_links.add(full_url)

            # Strategy 3: Numbered buttons
            for btn in soup.find_all(['button', 'a'], 
                                string=re.compile(r'^\d+$|next|prev|older|newer', re.I)):
                if btn.get('href'):
                    full_url = urljoin(blog_url, btn.get('href'))
                    if self.is_valid_url(full_url):
                        potential_links.add(full_url)

            # Convert to list and sort for consistency
            blog_links = sorted(potential_links)

            if not blog_links:
                print(" - No potential pagination links found")
                return None

            print(f" - Found {len(blog_links)} potential pagination links")

            # Prepare LLM prompt with stricter guidance
            prompt = f"""Analyze these URLs from {blog_url} and identify the pagination pattern.
                Return ONLY a JSON response with these possible fields:
                - 'type': Either 'query_param', 'path', or 'load_more'
                - 'pattern': The URL pattern with page number replaced by {{page}}
                - 'selector': CSS selector for pagination element if visible
                
                Example responses:
                {{"type": "query_param", "pattern": "{blog_url}?page={{page}}", "selector": ".pagination"}}
                {{"type": "path", "pattern": "{blog_url}/page/{{page}}/", "selector": "nav.pager"}}
                {{"type": "load_more", "selector": "#load-more"}}
                {{"type": null}} if no clear pattern
                
                URLs to analyze:
                {sorted(blog_links)}
                """

            # Get LLM analysis
            llm_response = litellm.completion(
                model="groq/deepseek-r1-distill-llama-70b",
                messages=[{"content": prompt, "role": "user"}],
                temperature=0.1
            )

            pattern = llm_response.choices[0].message.content.strip()
            json_str = self._extract_json_from_text(pattern)
            # Parse the JSON
            result = json.loads(json_str)

            # Validate the result structure
            if isinstance(result, dict) and result.get('type'):
                print(f" - LLM identified pattern: {result}")

                # Ensure pattern field exists for query_param/path types
                if result['type'] in ['query_param', 'path'] and 'pattern' not in result:
                    print(" - LLM response missing pattern field")
                    raise ValueError("Missing pattern field")

                self.source_website.pagination_pattern = f"{result}"
                self.source_website.save()
                return result

            if '{page}' not in pattern:
                print(f" - Invalid pattern format: {pattern}")
                return None

            # Verify the pattern works by testing page 2
            test_url = pattern.replace('{page}', '2')
            try:
                print(f" - Testing URL: {test_url}")
                resp = self.session.head(test_url, timeout=10)
                if resp.status_code == 200:
                    print(f" - Verified pagination pattern: {pattern}")
                    self.source_website.pagination_pattern = f"{{'type': 'auto', 'pattern': pattern}}"
                    self.source_website.save()
                    return {'type': 'auto', 'pattern': pattern}
            except Exception as e:
                print(f" - Pattern verification failed: {str(e)}")

            # Fallback to traditional detection if LLM fails
            print(" - Falling back to traditional detection")
            pat = self._traditional_pagination_detection(soup, blog_url)
            if pat:
                self.source_website.pagination_pattern = f"{pat}"
                self.source_website.save()
            return pat

        except Exception as e:
            print(f" - Pagination detection error: {str(e)}")
            return None

    def _extract_json_from_text(self, text):
        """Extract JSON string from potentially messy LLM response"""
        # Common cases we need to handle:
        # 1. Plain JSON response
        # 2. Markdown code block
        # 3. Text with JSON embedded
        # 4. Malformed JSON with extra text

        # Try direct parse first
        text = text.strip()
        if text.startswith('{') and text.endswith('}'):
            return text

        # Handle markdown code blocks
        md_match = re.search(r'```(?:json)?\n({.*?})\n```', text, re.DOTALL)
        if md_match:
            return md_match.group(1)

        # Handle JSON embedded in text
        brace_match = re.search(r'\{.*?\}', text, re.DOTALL)
        if brace_match:
            return brace_match.group(0)

        # Fallback - clean and try to parse anyway
        cleaned = re.sub(r'^[^{]+', '', text)  # Remove non-JSON prefix
        cleaned = re.sub(r'[^}]+$', '', cleaned)  # Remove non-JSON suffix
        return cleaned.strip()

    def _traditional_pagination_detection(self, soup, base_url):
        """Traditional pagination detection fallback"""
        # URL pattern detection
        url_pattern = self._detect_url_patterns(
            [a['href'] for a in soup.find_all('a', href=True)],
            base_url
        )
        if url_pattern:
            return url_pattern

        # Structural detection
        pagination = soup.find(['nav', 'div', 'ul'], 
                            class_=re.compile(r'pagination|pager', re.I))
        if pagination:
            return {'type': 'structural', 'selector': self._generate_selector(pagination)}

        return None

    def _detect_url_patterns(self, links, base_url):
        """Traditional URL pattern detection"""
        for link in links:
            # Query param pattern
            if '?page=' in link:
                return {
                    'type': 'query_param',
                    'pattern': link.split('?')[0] + '?page={page}'
                }
            # Path pattern
            if '/page/' in link:
                return {
                    'type': 'path',
                    'pattern': re.sub(r'/page/\d+', '/page/{page}', link)
                }
        return None

    def _generate_selector(self, element):
        """Generate CSS selector for an element"""
        if element.get('id'):
            return f"#{element['id']}"
        classes = element.get('class', [])
        if classes:
            return f".{'.'.join(classes)}"
        return element.name

    def extract_post_links(self, html):
        """Extract post links while ensuring they have valid paths"""
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        base_domain = urlparse(self.base_url).netloc

        # Common patterns for blog post containers
        container_selectors = [
            'article',
            'div[class*="post"]',
            'div[class*="blog"]',
            'div[class*="article"]',
            'h2[class*="post-title"]',
            'h2[class*="entry-title"]',
            'main li',
            'a[class*="post"]',
            'a[class*="blog"]',
            'a[class*="article"]',
        ]

        # First try structured containers
        for selector in container_selectors:
            for container in soup.select(selector):
                # Find all <a> inside the container
                for a in container.find_all('a', href=True):
                    href = self._get_valid_href(a, base_domain)
                    if href:
                        links.add(href)

        # If nothing found, fallback to scanning all <a> tags
        if not links:
            print(" - No links found using structured patterns, falling back to all <a> tags")
            for a in soup.find_all('a', href=True):
                href = self._get_valid_href(a, base_domain)
                if href and self._is_probable_blog_post(href):
                    links.add(href)

        return list(links)

    def _get_valid_href(self, tag, base_domain):
        """Helper to validate and normalize hrefs"""
        href = tag.get('href')
        if not href or href.startswith('#'):
            return None

        absolute_url = urljoin(self.base_url, href)
        parsed = urlparse(absolute_url)
        
        # Ensure it's from the same domain and not media/file link
        if parsed.netloc != base_domain:
            return None
        if re.search(r'\.(jpg|jpeg|png|gif|pdf|svg|css|js|ico)(\?|$)', parsed.path, re.I):
            return None

        return absolute_url

    def _is_probable_blog_post(self, href):
        """Heuristic to filter blog-like URLs"""
        # You can tweak this logic for your needs
        return re.search(r'/\d{4}/\d{2}/|/blog/|/post/|/article/|/how-to-|/home/', href)

    def _get_valid_href(self, elem, base_domain):
        """Extract and validate href from element"""
        href = None
        if elem.name == 'a':
            href = elem.get('href')
        else:
            link_elem = elem.find('a')
            if link_elem:
                href = link_elem.get('href')

        if not href:
            return None

        # Skip if href is just a fragment or query
        if href.startswith(('#', '?')):
            return None

        # Ensure URL has a path component
        parsed = urlparse(href)
        if not parsed.path or parsed.path == '/':
            return None

        # Convert to absolute URL
        full_url = urljoin(self.base_url, href)

        # Validate domain
        parsed_full = urlparse(full_url)
        if not parsed_full.netloc.endswith(base_domain):
            return None

        return full_url

    def _crawl_pagination_page(self, url, all_posts):
        """Helper to crawl a single pagination page"""
        try:
            response = self.session.get(url, timeout=10)
            new_posts = self.extract_post_links(response.text)

            if not new_posts or all(p in all_posts for p in new_posts):
                return True  # Stop pagination

            all_posts.update(new_posts)
            print(f" - Found {len(new_posts)} posts on {urlparse(url).path}")
            return False
        except Exception as e:
            print(f" - Error crawling {url}: {str(e)}")
            return True

    def _safe_parse_pagination_pattern(self, pattern_str):
        """Safely convert string pattern to dictionary"""
        if not pattern_str or not isinstance(pattern_str, str):
            return None

        try:
            # Handle cases where the string might use single quotes
            normalized_str = pattern_str.replace("'", '"')
            return json.loads(normalized_str)
        except json.JSONDecodeError:
            try:
                # Fallback to ast.literal_eval for more flexible parsing
                import ast
                return ast.literal_eval(pattern_str)
            except (ValueError, SyntaxError):
                print(f" - Could not parse pagination pattern: {pattern_str}")
                return None

    def _generate_pagination_urls(self, pagination_pattern):
        """Generate pagination URLs to exclude"""
        print(f" - Generating pagination URLs for pattern: {pagination_pattern}")
        urls = set()
        if pagination_pattern['type'] in ['query_param', 'path']:
            for page in range(1, 10):  # Test first 3 pages
                url = pagination_pattern['pattern'].replace('{page}', str(page))
                urls.add(url)
        return urls

    def _extract_and_validate_link(self, elem, base_domain):
        """Safely extract and validate link from element"""
        href = None
        if elem.name == 'a':
            href = elem.get('href')
        else:
            link_elem = elem.find('a')
            if link_elem:
                href = link_elem.get('href')

        return self._validate_and_normalize_url(href, base_domain) if href else None

    def _validate_and_normalize_url(self, href, base_domain):
        """Ensure URL is valid and properly formatted"""
        try:
            # Skip if href matches common non-post patterns
            if re.search(r'category|tag|author|date|feed', href, re.I):
                return None

            # Handle relative URLs
            if not urlparse(href).netloc:
                href = urljoin(f"https://{base_domain}", href)

            # Final validation
            parsed = urlparse(href)
            if (parsed.scheme in ('http', 'https') and 
                parsed.netloc.endswith(base_domain)):
                return href.rstrip('/')
        except Exception as e:
            print(f" - URL validation error for {href}: {str(e)}")
        return None

    def _extract_link_from_element(self, elem):
        """Helper to extract link from various element types"""
        if elem.name == 'a':
            return elem.get('href')

        # Check for nested <a> tags
        link_elem = elem.find('a')
        if link_elem and link_elem.get('href'):
            return link_elem.get('href')

        # Check for data attributes
        for attr in ['data-href', 'data-permalink', 'data-url']:
            if elem.get(attr):
                return elem.get(attr)

        # Check for onclick handlers with URLs
        if elem.get('onclick'):
            match = re.search(r'window\.location\.href=[\'"](.*?)[\'"]', elem.get('onclick'))
            if match:
                return match.group(1)

        return None

    def get_all_blog_posts_links(self):
        """Crawl through blog listing pages to find all posts"""

        blog_url = urljoin(self.base_url, self.blog_path)
        pagination = self._safe_parse_pagination_pattern(self.source_website.pagination_pattern)

        all_posts = set()

        try:
            # First page
            response = self.session.get(blog_url, timeout=10)
            posts = self.extract_post_links(response.text)

            if not posts:
                return []

            all_posts.update(posts)

            # Handle pagination if exists
            if pagination and 'pattern' in pagination:
                for page in range(2, self.max_pages + 1):
                    try:
                        if pagination.get('type') == 'query_param':
                            next_url = pagination['pattern'].format(page=page)
                        else:
                            next_url = pagination['pattern'].format(page=page)

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

    def update_blog_posts(self):
        post_urls = self.get_all_blog_posts_links()
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
        CrawlLog.objects.create(
            source=self.source_website,
            status='success',
            message=f'Crawled {len(post_urls)} posts, saved {saved_count} new ones',
            posts_found=len(post_urls)
        )

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

        print("1. Finding blog path")
        if self.source_website.blog_path:
            self.blog_path = self.source_website.blog_path

        if not self.blog_path:
            if not self.find_blog_path():
                CrawlLog.objects.create(
                    source=self.source_website,
                    status='error',
                    message='Could not identify blog section'
                )
                return False

        print("2. Discovering pagination pattern")
        blog_url = urljoin(self.base_url, self.blog_path)
        self.discover_pagination_pattern(blog_url)

        print("3. Update list of blog posts")
        self.update_blog_posts()

        print(f"Crawling completed in {time.time() - start_time:.2f} seconds")
        return True

def add_site(domain):
    """Run the crawler for a single domain"""
    BlogCrawler(domain)
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
