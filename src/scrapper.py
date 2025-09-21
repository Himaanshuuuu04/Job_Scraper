
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import asyncio
from collections import deque
from bs4 import BeautifulSoup
import re
import urllib.parse

class BrowserManager:
    def __init__(self, max_concurrent_tabs=2, headless=True):
        self.playwright_context = None
        self.playwright = None
        self.browser = None
        self.max_concurrent_tabs = max_concurrent_tabs
        self.headless = headless
        self.semaphore = asyncio.Semaphore(max_concurrent_tabs)
        self.tab_pool = deque()
        self.active_tabs = set()
        self.search_cache = {}  # Cache search results to avoid duplicate queries
    
    def filter_and_categorize_links(self, html_content, company_name, query_type="general"):
        """Use BeautifulSoup to parse page and intelligently filter/categorize links"""
        soup = BeautifulSoup(html_content, 'html.parser')
        categorized_links = {
            'website': [],
            'linkedin': [],
            'careers': [],
            'jobs_platform': [],
            'other': []
        }
        
        # Find all links in the page
        all_links = soup.find_all('a', href=True)
        
        company_clean = company_name.lower().replace(' ', '').replace('-', '').replace('_', '')
        
        for link_elem in all_links:
            href = link_elem.get('href', '')
            text = link_elem.get_text(strip=True).lower()
            title = link_elem.get('title', '').lower()
            
            # Skip invalid links
            if not href or not href.startswith('http') or 'duckduckgo.com' in href:
                continue
            
            href_lower = href.lower()
            
            # Categorize links based on domain and content
            if self._is_job_platform(href_lower):
                categorized_links['jobs_platform'].append({
                    'url': href,
                    'text': text,
                    'title': title,
                    'score': self._calculate_relevance_score(href, text, title, company_name, 'jobs')
                })
            elif 'linkedin.com' in href_lower and ('company' in href_lower or 'in/' in href_lower):
                categorized_links['linkedin'].append({
                    'url': href,
                    'text': text,
                    'title': title,
                    'score': self._calculate_relevance_score(href, text, title, company_name, 'linkedin')
                })
            elif self._is_careers_page(href_lower, text, title):
                categorized_links['careers'].append({
                    'url': href,
                    'text': text,
                    'title': title,
                    'score': self._calculate_relevance_score(href, text, title, company_name, 'careers')
                })
            elif self._is_company_website(href_lower, company_name):
                categorized_links['website'].append({
                    'url': href,
                    'text': text,
                    'title': title,
                    'score': self._calculate_relevance_score(href, text, title, company_name, 'website')
                })
            else:
                # Only include other links if they seem relevant
                if company_clean in href_lower or any(word in text for word in company_name.lower().split()):
                    categorized_links['other'].append({
                        'url': href,
                        'text': text,
                        'title': title,
                        'score': self._calculate_relevance_score(href, text, title, company_name, 'other')
                    })
        
        # Sort each category by relevance score and return top results
        for category in categorized_links:
            categorized_links[category] = sorted(
                categorized_links[category], 
                key=lambda x: x['score'], 
                reverse=True
            )[:5]  # Keep top 5 for each category
        
        return categorized_links
    
    def _is_job_platform(self, url):
        """Check if URL is from a known job platform"""
        job_platforms = [
            'lever.co', 'greenhouse.io', 'zohorecruit.com', 'zoho.recruit',
            'smartrecruiters.com', 'workday.com', 'bamboohr.com', 'jobvite.com',
            'icims.com', 'successfactors.com', 'talentsoft.com', 'cornerstone.ondemand.com'
        ]
        return any(platform in url for platform in job_platforms)
    
    def _is_careers_page(self, url, text, title):
        """Check if this appears to be a careers page"""
        career_indicators = ['careers', 'jobs', 'employment', 'opportunities', 'hiring', 'openings', 'join-us', 'work-with-us', 'apply']
        
        # Check URL path
        if any(indicator in url for indicator in career_indicators):
            return True
        
        # Check link text and title
        combined_text = f"{text} {title}".lower()
        if any(indicator in combined_text for indicator in career_indicators):
            return True
            
        return False
    
    def _is_company_website(self, url, company_name):
        """Check if URL appears to be the company's official website"""
        company_clean = company_name.lower().replace(' ', '').replace('-', '').replace('_', '').replace('.', '')
        url_domain = url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0]
        
        # Exclude known non-company domains
        excluded_domains = [
            'linkedin.com', 'facebook.com', 'twitter.com', 'youtube.com', 'instagram.com',
            'glassdoor.com', 'indeed.com', 'monster.com', 'ziprecruiter.com', 'wikipedia.org',
            'crunchbase.com', 'bloomberg.com', 'reuters.com', 'forbes.com'
        ]
        
        if any(excluded in url for excluded in excluded_domains):
            return False
        
        # Check if company name appears in domain
        return company_clean[:8] in url_domain.replace('-', '').replace('_', '')
    
    def _calculate_relevance_score(self, url, text, title, company_name, category):
        """Calculate relevance score for a link"""
        score = 0
        company_words = company_name.lower().split()
        combined_text = f"{url} {text} {title}".lower()
        
        # Company name matching
        for word in company_words:
            if len(word) > 2:  # Skip very short words
                if word in combined_text:
                    score += 10
        
        # Category-specific scoring
        if category == 'jobs':
            job_keywords = ['jobs', 'careers', 'hiring', 'openings', 'apply', 'employment']
            score += sum(5 for keyword in job_keywords if keyword in combined_text)
        elif category == 'linkedin':
            if 'company' in combined_text:
                score += 15
        elif category == 'careers':
            career_keywords = ['careers', 'jobs', 'work', 'team', 'opportunities']
            score += sum(3 for keyword in career_keywords if keyword in combined_text)
        elif category == 'website':
            # Prefer shorter, simpler URLs (likely official sites)
            if len(url) < 50:
                score += 5
            if url.endswith('.com'):
                score += 5
        
        return score
    
    async def initialize(self):
        """Initialize the browser once"""
        stealth = Stealth()
        self.playwright_context = stealth.use_async(async_playwright())
        self.playwright = await self.playwright_context.__aenter__()
        
        # Launch browser in headless mode by default to avoid multiple windows
        self.browser = await self.playwright.firefox.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage'] if self.headless else []
        )
        
        # Pre-create only one tab initially to avoid too many windows
        page = await self.browser.new_page()
        self.tab_pool.append(page)
    
    async def _get_tab(self):
        """Get a tab from the pool or create a new one"""
        if self.tab_pool:
            return self.tab_pool.popleft()
        else:
            return await self.browser.new_page()
    
    async def _return_tab(self, page):
        """Return a tab to the pool for reuse"""
        try:
            # Clear the page for reuse
            await page.goto('about:blank')
            self.tab_pool.append(page)
        except Exception as e:
            # If clearing fails, close the tab and don't return it to pool
            try:
                await page.close()
            except:
                pass
    
    async def search(self, query: str, company_name: str = ""):
        """Perform search using existing browser with BeautifulSoup parsing and intelligent filtering"""
        if not self.browser:
            raise Exception("Browser not initialized. Call initialize() first.")
        
        # Check cache first to avoid duplicate searches
        cache_key = f"{query}_{company_name}"
        if cache_key in self.search_cache:
            print(f"Using cached results for: {query[:50]}...")
            return self.search_cache[cache_key]
        
        async with self.semaphore:  # Limit concurrent tabs
            page = await self._get_tab()
            self.active_tabs.add(page)
            
            try:
                # URL encode the query properly
                encoded_query = urllib.parse.quote_plus(query)
                search_url = f"https://duckduckgo.com/?q={encoded_query}"
                
                print(f"Searching: {query[:50]}...")
                await page.goto(search_url, timeout=30000)
                
                # Wait for page to load and get full HTML content
                await page.wait_for_load_state('networkidle', timeout=10000)
                html_content = await page.content()
                
                # Use BeautifulSoup for intelligent parsing and filtering
                if company_name:
                    categorized_links = self.filter_and_categorize_links(html_content, company_name)
                    
                    # Extract URLs from categorized results, prioritizing by category
                    links = []
                    # Priority order: jobs_platform -> linkedin -> careers -> website -> other
                    for category in ['jobs_platform', 'linkedin', 'careers', 'website', 'other']:
                        for link_data in categorized_links[category]:
                            if link_data['url'] not in links:  # Avoid duplicates
                                links.append(link_data['url'])
                else:
                    # Fallback to basic link extraction if no company name provided
                    soup = BeautifulSoup(html_content, 'html.parser')
                    links = []
                    
                    # Try DuckDuckGo result selectors
                    selectors = [
                        'a[data-testid="result-title-a"]',
                        'a.result__a',
                        'h2.result__title a',
                        '.results .result a'
                    ]
                    
                    for selector in selectors:
                        try:
                            result_links = soup.select(selector)
                            for link in result_links:
                                url = link.get('href')
                                if url and url.startswith("http") and "duckduckgo.com" not in url:
                                    if url not in links:  # Avoid duplicates
                                        links.append(url)
                            if links:  # If we found links with this selector, stop trying others
                                break
                        except Exception as e:
                            continue
                
                print(f"Found {len(links)} filtered links for: {query[:30]}...")
                
                # Cache the results
                self.search_cache[cache_key] = links
                return links
            
            except Exception as e:
                print(f"Error in search '{query}': {e}")
                return []
            
            finally:
                self.active_tabs.discard(page)
                await self._return_tab(page)
    
    async def search_multiple(self, queries, company_name=""):
        """Perform multiple searches with controlled concurrency and intelligent filtering"""
        if not queries:
            return []
        
        # Remove duplicate queries to avoid unnecessary searches
        unique_queries = list(dict.fromkeys(queries))  # Preserves order while removing duplicates
        print(f"Performing {len(unique_queries)} unique searches (was {len(queries)})")
        
        # Process searches in smaller batches to avoid too many concurrent tabs
        batch_size = min(self.max_concurrent_tabs, 2)  # Reduce batch size for more stable processing
        all_links = []
        
        for i in range(0, len(unique_queries), batch_size):
            batch = unique_queries[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(unique_queries) + batch_size - 1)//batch_size}")
            
            # Create tasks with company name context
            tasks = [self.search(query, company_name) for query in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results and handle exceptions
            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Error in search '{batch[j]}': {result}")
                else:
                    all_links.extend(result)
            
            # Small delay between batches to be respectful to the search engine
            if i + batch_size < len(unique_queries):
                await asyncio.sleep(2)  # Slightly longer delay
        
        # Remove duplicates from final results while preserving order
        seen = set()
        unique_links = []
        for link in all_links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        print(f"Final result: {len(unique_links)} unique links from {len(all_links)} total")
        return unique_links
    
    async def search_with_categorization(self, queries, company_name):
        """Perform searches and return categorized results"""
        if not queries or not company_name:
            return {}
        
        all_categorized = {
            'website': [],
            'linkedin': [],
            'careers': [],
            'jobs_platform': [],
            'other': []
        }
        
        # Process queries in batches
        batch_size = min(self.max_concurrent_tabs, 2)
        
        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            
            for query in batch:
                try:
                    cache_key = f"{query}_{company_name}"
                    
                    if cache_key not in self.search_cache:
                        # Perform search if not cached
                        await self.search(query, company_name)
                    
                    # Get page content and categorize
                    async with self.semaphore:
                        page = await self._get_tab()
                        try:
                            encoded_query = urllib.parse.quote_plus(query)
                            search_url = f"https://duckduckgo.com/?q={encoded_query}"
                            await page.goto(search_url, timeout=30000)
                            await page.wait_for_load_state('networkidle', timeout=10000)
                            html_content = await page.content()
                            
                            categorized = self.filter_and_categorize_links(html_content, company_name)
                            
                            # Merge results
                            for category in all_categorized:
                                all_categorized[category].extend(categorized[category])
                                
                        finally:
                            await self._return_tab(page)
                
                except Exception as e:
                    print(f"Error in categorized search '{query}': {e}")
            
            # Delay between batches
            if i + batch_size < len(queries):
                await asyncio.sleep(2)
        
        # Remove duplicates and sort by score
        for category in all_categorized:
            seen_urls = set()
            unique_links = []
            for link_data in all_categorized[category]:
                if link_data['url'] not in seen_urls:
                    seen_urls.add(link_data['url'])
                    unique_links.append(link_data)
            
            all_categorized[category] = sorted(unique_links, key=lambda x: x['score'], reverse=True)[:3]
        
        return all_categorized
    
    async def close(self):
        """Close the browser and cleanup"""
        # Close all tabs in the pool
        while self.tab_pool:
            page = self.tab_pool.popleft()
            try:
                await page.close()
            except:
                pass
        
        # Close any remaining active tabs
        for page in list(self.active_tabs):
            try:
                await page.close()
            except:
                pass
        self.active_tabs.clear()
        
        if self.browser:
            await self.browser.close()
        if self.playwright_context:
            await self.playwright_context.__aexit__(None, None, None)

# Backward compatibility function
async def duckduckgo_search(query: str, company_name: str = ""):
    """Legacy function for single search - creates and closes browser"""
    manager = BrowserManager()
    try:
        await manager.initialize()
        return await manager.search(query, company_name)
    finally:
        await manager.close()

