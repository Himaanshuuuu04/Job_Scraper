import asyncio
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse
import pandas as pd
from collections import deque

class JobScraper:
    def __init__(self, browser_manager, max_concurrent_scrapes=3):
        self.browser_manager = browser_manager
        self.total_jobs_scraped = 0
        self.max_total_jobs = 200
        self.max_jobs_per_company = 3
        self.max_concurrent_scrapes = max_concurrent_scrapes
        self.scrape_semaphore = asyncio.Semaphore(max_concurrent_scrapes)
        self.scraper_tab_pool = deque()
        self.active_scraper_tabs = set()
        
    async def _get_scraper_tab(self):
        """Get a tab for scraping from the pool or create a new one"""
        if self.scraper_tab_pool:
            return self.scraper_tab_pool.popleft()
        else:
            return await self.browser_manager.browser.new_page()
    
    async def _return_scraper_tab(self, page):
        """Return a scraper tab to the pool for reuse"""
        try:
            # Clear the page for reuse
            await page.goto('about:blank')
            self.scraper_tab_pool.append(page)
        except Exception as e:
            # If clearing fails, close the tab and don't return it to pool
            try:
                await page.close()
            except:
                pass
    
    async def scrape_jobs_from_url(self, company_name, url, url_type="careers"):
        """Scrape job postings from a given URL"""
        if not url or self.total_jobs_scraped >= self.max_total_jobs:
            return []
            
        print(f"Scraping {url_type} page for {company_name}: {url}")
        
        async with self.scrape_semaphore:  # Limit concurrent scraping
            page = await self._get_scraper_tab()
            self.active_scraper_tabs.add(page)
            jobs = []
            
            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Check for common job board platforms and scrape accordingly
                if 'lever.co' in url:
                    jobs = await self._scrape_lever_jobs(page, company_name, url)
                elif 'greenhouse.io' in url:
                    jobs = await self._scrape_greenhouse_jobs(page, company_name, url)
                elif 'zoho.recruit' in url or 'zohorecruit.com' in url:
                    jobs = await self._scrape_zoho_jobs(page, company_name, url)
                elif 'smartrecruiters.com' in url:
                    jobs = await self._scrape_smartrecruiters_jobs(page, company_name, url)
                elif 'workday.com' in url:
                    jobs = await self._scrape_workday_jobs(page, company_name, url)
                else:
                    # Generic scraping for other platforms
                    jobs = await self._scrape_generic_jobs(page, company_name, url)
                    
                # Limit jobs per company and update total count
                jobs = jobs[:self.max_jobs_per_company]
                self.total_jobs_scraped += len(jobs)
                
                print(f"Found {len(jobs)} jobs for {company_name}")
                return jobs
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                return []
            finally:
                self.active_scraper_tabs.discard(page)
                await self._return_scraper_tab(page)
    
    async def _scrape_lever_jobs(self, page, company_name, base_url):
        """Scrape jobs from Lever platform"""
        jobs = []
        try:
            # Wait for job listings to load
            await page.wait_for_selector('.posting', timeout=5000)
            job_elements = await page.query_selector_all('.posting')
            
            for job_elem in job_elements[:self.max_jobs_per_company]:
                try:
                    title = await job_elem.query_selector('.posting-title')
                    title_text = await title.inner_text() if title else "N/A"
                    
                    location = await job_elem.query_selector('.posting-categories .location')
                    location_text = await location.inner_text() if location else "N/A"
                    
                    link = await job_elem.query_selector('a')
                    job_url = await link.get_attribute('href') if link else ""
                    if job_url and not job_url.startswith('http'):
                        job_url = urljoin(base_url, job_url)
                    
                    jobs.append({
                        'company_name': company_name,
                        'job_title': title_text.strip(),
                        'job_location': location_text.strip(),
                        'job_url': job_url,
                        'posting_date': 'N/A',
                        'job_description': 'N/A',
                        'platform': 'Lever'
                    })
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error scraping Lever jobs: {e}")
        
        return jobs
    
    async def _scrape_greenhouse_jobs(self, page, company_name, base_url):
        """Scrape jobs from Greenhouse platform"""
        jobs = []
        try:
            await page.wait_for_selector('.opening', timeout=5000)
            job_elements = await page.query_selector_all('.opening')
            
            for job_elem in job_elements[:self.max_jobs_per_company]:
                try:
                    title = await job_elem.query_selector('a')
                    title_text = await title.inner_text() if title else "N/A"
                    job_url = await title.get_attribute('href') if title else ""
                    
                    location = await job_elem.query_selector('.location')
                    location_text = await location.inner_text() if location else "N/A"
                    
                    if job_url and not job_url.startswith('http'):
                        job_url = urljoin(base_url, job_url)
                    
                    jobs.append({
                        'company_name': company_name,
                        'job_title': title_text.strip(),
                        'job_location': location_text.strip(),
                        'job_url': job_url,
                        'posting_date': 'N/A',
                        'job_description': 'N/A',
                        'platform': 'Greenhouse'
                    })
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error scraping Greenhouse jobs: {e}")
        
        return jobs
    
    async def _scrape_zoho_jobs(self, page, company_name, base_url):
        """Scrape jobs from Zoho Recruit platform"""
        jobs = []
        try:
            # Try multiple selectors for Zoho
            selectors = ['.job-item', '.job-listing', '.career-item', 'tr[onclick]']
            
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=3000)
                    job_elements = await page.query_selector_all(selector)
                    
                    if job_elements:
                        for job_elem in job_elements[:self.max_jobs_per_company]:
                            try:
                                # Extract job details based on Zoho structure
                                title_elem = await job_elem.query_selector('a, .job-title, td:first-child')
                                title_text = await title_elem.inner_text() if title_elem else "N/A"
                                
                                # Try to get job URL
                                link_elem = await job_elem.query_selector('a')
                                job_url = await link_elem.get_attribute('href') if link_elem else ""
                                if not job_url and job_elem.get_attribute:
                                    onclick = await job_elem.get_attribute('onclick')
                                    if onclick and 'window.open' in onclick:
                                        import re
                                        url_match = re.search(r"window\.open\('([^']+)'", onclick)
                                        if url_match:
                                            job_url = url_match.group(1)
                                
                                if job_url and not job_url.startswith('http'):
                                    job_url = urljoin(base_url, job_url)
                                
                                jobs.append({
                                    'company_name': company_name,
                                    'job_title': title_text.strip(),
                                    'job_location': 'N/A',
                                    'job_url': job_url,
                                    'posting_date': 'N/A',
                                    'job_description': 'N/A',
                                    'platform': 'Zoho Recruit'
                                })
                            except Exception as e:
                                continue
                        break
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error scraping Zoho jobs: {e}")
        
        return jobs
    
    async def _scrape_smartrecruiters_jobs(self, page, company_name, base_url):
        """Scrape jobs from SmartRecruiters platform"""
        jobs = []
        try:
            await page.wait_for_selector('.opening-job', timeout=5000)
            job_elements = await page.query_selector_all('.opening-job')
            
            for job_elem in job_elements[:self.max_jobs_per_company]:
                try:
                    title = await job_elem.query_selector('.job-title a, h4 a')
                    title_text = await title.inner_text() if title else "N/A"
                    job_url = await title.get_attribute('href') if title else ""
                    
                    location = await job_elem.query_selector('.job-location')
                    location_text = await location.inner_text() if location else "N/A"
                    
                    if job_url and not job_url.startswith('http'):
                        job_url = urljoin(base_url, job_url)
                    
                    jobs.append({
                        'company_name': company_name,
                        'job_title': title_text.strip(),
                        'job_location': location_text.strip(),
                        'job_url': job_url,
                        'posting_date': 'N/A',
                        'job_description': 'N/A',
                        'platform': 'SmartRecruiters'
                    })
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error scraping SmartRecruiters jobs: {e}")
        
        return jobs
    
    async def _scrape_workday_jobs(self, page, company_name, base_url):
        """Scrape jobs from Workday platform"""
        jobs = []
        try:
            await page.wait_for_selector('[data-automation-id="jobTitle"]', timeout=5000)
            job_elements = await page.query_selector_all('[data-automation-id="jobTitle"]')
            
            for job_elem in job_elements[:self.max_jobs_per_company]:
                try:
                    title_text = await job_elem.inner_text()
                    job_url = await job_elem.get_attribute('href')
                    
                    if job_url and not job_url.startswith('http'):
                        job_url = urljoin(base_url, job_url)
                    
                    jobs.append({
                        'company_name': company_name,
                        'job_title': title_text.strip(),
                        'job_location': 'N/A',
                        'job_url': job_url,
                        'posting_date': 'N/A',
                        'job_description': 'N/A',
                        'platform': 'Workday'
                    })
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error scraping Workday jobs: {e}")
        
        return jobs
    
    async def _scrape_generic_jobs(self, page, company_name, base_url):
        """Generic job scraping for unknown platforms"""
        jobs = []
        try:
            # Common selectors for job listings
            selectors = [
                'a[href*="job"]', 'a[href*="career"]', 'a[href*="position"]',
                '.job', '.career', '.position', '.opening',
                '[class*="job"]', '[class*="career"]', '[class*="position"]'
            ]
            
            for selector in selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        for elem in elements[:self.max_jobs_per_company]:
                            try:
                                title_text = await elem.inner_text()
                                job_url = await elem.get_attribute('href')
                                
                                # Filter out non-job links
                                if not any(keyword in title_text.lower() for keyword in ['job', 'career', 'position', 'opening', 'role']):
                                    continue
                                
                                if job_url and not job_url.startswith('http'):
                                    job_url = urljoin(base_url, job_url)
                                
                                jobs.append({
                                    'company_name': company_name,
                                    'job_title': title_text.strip()[:100],  # Limit title length
                                    'job_location': 'N/A',
                                    'job_url': job_url,
                                    'posting_date': 'N/A',
                                    'job_description': 'N/A',
                                    'platform': 'Generic'
                                })
                            except Exception as e:
                                continue
                        
                        if jobs:  # If we found jobs with this selector, break
                            break
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error in generic job scraping: {e}")
        
        return jobs
    
    async def scrape_multiple_urls(self, urls_data):
        """Scrape multiple URLs concurrently
        Args:
            urls_data: List of tuples (company_name, url, url_type)
        """
        if not urls_data or self.total_jobs_scraped >= self.max_total_jobs:
            return []
        
        # Filter out URLs if we've reached the limit
        remaining_slots = self.max_total_jobs - self.total_jobs_scraped
        if remaining_slots <= 0:
            return []
        
        tasks = []
        for company_name, url, url_type in urls_data:
            if self.total_jobs_scraped >= self.max_total_jobs:
                break
            tasks.append(self.scrape_jobs_from_url(company_name, url, url_type))
        
        if not tasks:
            return []
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results and handle exceptions
        all_jobs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                company_name, url, url_type = urls_data[i]
                print(f"Error scraping {company_name} ({url_type}): {result}")
            else:
                all_jobs.extend(result)
        
        return all_jobs
    
    async def cleanup_scraper_tabs(self):
        """Clean up all scraper tabs"""
        # Close all tabs in the pool
        while self.scraper_tab_pool:
            page = self.scraper_tab_pool.popleft()
            try:
                await page.close()
            except:
                pass
        
        # Close any remaining active tabs
        for page in list(self.active_scraper_tabs):
            try:
                await page.close()
            except:
                pass
        self.active_scraper_tabs.clear()
    
    def has_reached_limit(self):
        """Check if we've reached the 200 job limit"""
        return self.total_jobs_scraped >= self.max_total_jobs