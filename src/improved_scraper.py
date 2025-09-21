# Improved Data Enrichment and Job Scraping Script
# Provides data in the exact format requested by the user

import pandas as pd
import asyncio
from datetime import datetime
import re
from urllib.parse import urlparse, urljoin
import sys
from pathlib import Path

# Add parent directory to path for data access
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapper import BrowserManager
from job_scraper import JobScraper

def extract_industry_keywords(description):
    """Extract relevant industry keywords from company description"""
    keywords = []
    desc_lower = description.lower()
    
    # Industry categories with associated keywords
    industry_map = {
        'technology': ['software', 'tech', 'ai', 'machine learning', 'cloud', 'saas', 'platform'],
        'healthcare': ['health', 'medical', 'hospital', 'pharmacy', 'biotech', 'clinical'],
        'finance': ['financial', 'banking', 'investment', 'insurance', 'fintech', 'payments'],
        'energy': ['solar', 'renewable', 'energy', 'power', 'electric', 'green', 'sustainability'],
        'manufacturing': ['manufacturing', 'industrial', 'production', 'factory', 'automotive'],
        'retail': ['retail', 'consumer', 'shopping', 'commerce', 'brand', 'marketplace'],
        'consulting': ['consulting', 'advisory', 'services', 'solutions', 'strategy'],
        'education': ['education', 'learning', 'training', 'university', 'school'],
        'media': ['media', 'marketing', 'advertising', 'content', 'digital', 'creative']
    }
    
    for category, terms in industry_map.items():
        if any(term in desc_lower for term in terms):
            keywords.append(category)
    
    return keywords[:2]  # Return max 2 keywords to keep queries focused

async def scrape_individual_job_details(browser_manager, job_url, company_name):
    """Scrape individual job posting details"""
    try:
        if not job_url or job_url == 'nan' or pd.isna(job_url):
            return None, None
            
        page = await browser_manager._get_tab()
        await page.goto(job_url, timeout=30000)
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # Try different selectors for job titles
        title_selectors = [
            'h1', '.job-title', '.posting-headline', '.job-header h1',
            '[data-automation-id="jobTitle"]', '.posting-title',
            '.job-name', '.position-title', '.role-title'
        ]
        
        job_title = None
        for selector in title_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    title_text = await element.inner_text()
                    if title_text and len(title_text.strip()) > 0:
                        job_title = title_text.strip()
                        break
            except:
                continue
        
        await browser_manager._return_tab(page)
        return job_url, job_title or "Job Title Not Found"
        
    except Exception as e:
        print(f"Error scraping job details from {job_url}: {e}")
        return job_url, "Job Title Not Available"

async def process_company_jobs(browser_manager, job_scraper, company_name, jobs_url, careers_url):
    """Process jobs for a single company and return up to 3 job postings"""
    jobs = []
    
    # Try jobs URL first, then careers URL
    urls_to_try = []
    if jobs_url and jobs_url != '' and not pd.isna(jobs_url):
        urls_to_try.append((jobs_url, "jobs"))
    if careers_url and careers_url != '' and not pd.isna(careers_url):
        urls_to_try.append((careers_url, "careers"))
    
    for url, url_type in urls_to_try:
        try:
            scraped_jobs = await job_scraper.scrape_jobs_from_url(company_name, url, url_type)
            jobs.extend(scraped_jobs)
            if len(jobs) >= 3:
                break
        except Exception as e:
            print(f"Error scraping {url_type} for {company_name}: {e}")
            continue
    
    # If we still don't have jobs, try a more aggressive search
    if len(jobs) == 0 and (jobs_url or careers_url):
        # Try to find job links on the careers page
        try:
            search_url = jobs_url or careers_url
            job_links = await find_job_links_on_page(browser_manager, search_url, company_name)
            
            # Get details for up to 3 job links
            for job_link in job_links[:3]:
                job_url, job_title = await scrape_individual_job_details(browser_manager, job_link, company_name)
                if job_url:
                    jobs.append({
                        'company_name': company_name,
                        'job_title': job_title,
                        'job_location': 'N/A',
                        'job_url': job_url,
                        'posting_date': 'N/A',
                        'job_description': 'N/A',
                        'platform': 'Custom'
                    })
        except Exception as e:
            print(f"Error in aggressive job search for {company_name}: {e}")
    
    return jobs[:3]  # Return max 3 jobs

async def find_job_links_on_page(browser_manager, url, company_name):
    """Find job posting links on a careers page"""
    try:
        page = await browser_manager._get_tab()
        await page.goto(url, timeout=30000)
        await page.wait_for_load_state('networkidle', timeout=10000)
        
        # Look for links that might be job postings
        job_selectors = [
            'a[href*="job"]', 'a[href*="position"]', 'a[href*="opening"]',
            'a[href*="career"]', 'a[href*="apply"]', '.job-link a',
            '.position-link a', '.opening-link a', '.job-title a'
        ]
        
        job_links = []
        for selector in job_selectors:
            try:
                elements = await page.query_selector_all(selector)
                for element in elements[:5]:  # Check first 5 matches per selector
                    href = await element.get_attribute('href')
                    if href:
                        # Convert relative URLs to absolute
                        if not href.startswith('http'):
                            href = urljoin(url, href)
                        if href not in job_links:
                            job_links.append(href)
                        if len(job_links) >= 10:  # Limit to 10 potential job links
                            break
            except:
                continue
            
            if len(job_links) >= 10:
                break
        
        await browser_manager._return_tab(page)
        return job_links[:5]  # Return top 5 job links
        
    except Exception as e:
        print(f"Error finding job links on {url}: {e}")
        return []

async def main():
    """Main function to create the exact format requested"""
    
    # Read the Excel file
    data_file = project_root / "data" / "Data.xlsx"
    try:
        df = pd.read_excel(data_file)
        print(f"Loaded {len(df)} companies from {data_file}")
    except FileNotFoundError:
        print(f"Error: {data_file} file not found!")
        return
    except Exception as e:
        print(f"Error reading {data_file}: {e}")
        return

    # Initialize new columns if they don't exist
    required_columns = [
        'Website URL', 'Linkedin URL', 'Careers Page URL', 'Job listings page URL',
        'job post1 URL', 'job post1 title', 'job post2 URL', 'job post2 title', 
        'job post3 URL', 'job post3 title'
    ]
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = ''

    # Initialize browser manager and job scraper
    browser_manager = BrowserManager(max_concurrent_tabs=2, headless=True)
    job_scraper = JobScraper(browser_manager, max_concurrent_scrapes=1)
    
    try:
        await browser_manager.initialize()
        print("Browser initialized successfully!")
        
        # Process companies (limit to first 10 for demonstration)
        max_companies = len(df)
        print(f"Processing first {max_companies} companies...")
        
        for idx in range(max_companies):
            row = df.iloc[idx]
            company_name = str(row['Company Name'])
            company_desc = str(row['Company Description'])
            
            print(f"\n--- Processing Company {idx+1}/{max_companies}: {company_name} ---")
            
            # Phase 1: URL Discovery (if not already populated)
            if not row['Website URL'] or pd.isna(row['Website URL']) or row['Website URL'] == '':
                print("Discovering company URLs...")
                
                # Create search queries
                search_queries = [
                    f'{company_name}',
                    f'{company_name} official website',
                    f'{company_name} linkedin company',
                    f'{company_name} careers',
                    f'{company_name} jobs',
                    f'{company_name} careers page',
                    f'{company_name} job openings'
                ]
                
                try:
                    all_links = await browser_manager.search_multiple(search_queries, company_name)
                    
                    # Categorize links
                    website_url = ''
                    linkedin_url = ''
                    careers_url = ''
                    jobs_url = ''
                    
                    for link in all_links:
                        link_lower = link.lower()
                        
                        # Job platforms (highest priority)
                        job_platforms = ['lever.co', 'greenhouse.io', 'zohorecruit.com', 'zoho.recruit', 
                                       'smartrecruiters.com', 'workday.com', 'bamboohr.com', 'jobvite.com', 
                                       'icims.com', 'teamtailor.com', 'personio.com']
                        if any(platform in link_lower for platform in job_platforms) and not jobs_url:
                            jobs_url = link
                            continue
                        
                        # LinkedIn
                        if 'linkedin.com' in link_lower and 'company' in link_lower and not linkedin_url:
                            linkedin_url = link
                            continue
                        
                        # Careers pages
                        career_keywords = ['careers', 'jobs', 'employment', 'opportunities', 'hiring', 'openings']
                        if any(keyword in link_lower for keyword in career_keywords) and not careers_url:
                            excluded_sites = ['glassdoor.com', 'indeed.com', 'monster.com', 'ziprecruiter.com']
                            if not any(site in link_lower for site in excluded_sites):
                                careers_url = link
                                continue
                        
                        # Company website
                        if not website_url:
                            excluded_domains = ['linkedin.com', 'facebook.com', 'twitter.com', 'youtube.com', 
                                              'glassdoor.com', 'indeed.com', 'wikipedia.org', 'crunchbase.com']
                            if not any(excluded in link_lower for excluded in excluded_domains):
                                website_url = link
                    
                    # Update DataFrame
                    df.at[idx, 'Website URL'] = website_url
                    df.at[idx, 'Linkedin URL'] = linkedin_url
                    df.at[idx, 'Careers Page URL'] = careers_url
                    df.at[idx, 'Job listings page URL'] = jobs_url
                    
                    print(f"Found URLs - Website: {bool(website_url)}, LinkedIn: {bool(linkedin_url)}, Careers: {bool(careers_url)}, Jobs: {bool(jobs_url)}")
                    
                except Exception as e:
                    print(f"Error during URL discovery: {e}")
            
            # Phase 2: Job Scraping
            current_jobs_url = df.at[idx, 'Job listings page URL']
            current_careers_url = df.at[idx, 'Careers Page URL']
            
            # Check if we already have job data
            has_existing_jobs = any([
                df.at[idx, 'job post1 URL'] and not pd.isna(df.at[idx, 'job post1 URL']) and df.at[idx, 'job post1 URL'] != '',
                df.at[idx, 'job post2 URL'] and not pd.isna(df.at[idx, 'job post2 URL']) and df.at[idx, 'job post2 URL'] != '',
                df.at[idx, 'job post3 URL'] and not pd.isna(df.at[idx, 'job post3 URL']) and df.at[idx, 'job post3 URL'] != ''
            ])
            
            if not has_existing_jobs and (current_jobs_url or current_careers_url):
                print("Scraping job postings...")
                try:
                    jobs = await process_company_jobs(browser_manager, job_scraper, company_name, current_jobs_url, current_careers_url)
                    
                    # Populate job data
                    for i, job in enumerate(jobs[:3]):
                        df.at[idx, f'job post{i+1} URL'] = job.get('job_url', '')
                        df.at[idx, f'job post{i+1} title'] = job.get('job_title', '')
                    
                    print(f"Found {len(jobs)} job postings")
                    
                except Exception as e:
                    print(f"Error during job scraping: {e}")
            
            # Small delay between companies
            await asyncio.sleep(2)
        
    finally:
        await job_scraper.cleanup_scraper_tabs()
        await browser_manager.close()
        print("Browser closed successfully!")
    
    # Save the results
    output_file = project_root / "output" / "Data_enriched_improved.xlsx"
    
    # Clean up the data - remove extra columns and ensure proper format
    final_columns = [
        'Company Name', 'Company Description', 'Website URL', 'Linkedin URL', 
        'Careers Page URL', 'Job listings page URL', 'job post1 URL', 'job post1 title',
        'job post2 URL', 'job post2 title', 'job post3 URL', 'job post3 title'
    ]
    
    # Create final dataframe with only the required columns
    df_final = df[final_columns].copy()
    
    # Replace NaN values with empty strings for cleaner output
    df_final = df_final.fillna('')
    
    # Save to Excel
    df_final.to_excel(output_file, index=False)
    
    print(f"\n" + "="*60)
    print("IMPROVED DATA ENRICHMENT COMPLETED")
    print("="*60)
    print(f"📊 Total companies processed: {max_companies}")
    
    # Count companies with data
    companies_with_urls = 0
    companies_with_jobs = 0
    
    for idx in range(max_companies):
        has_urls = any([
            df_final.iloc[idx]['Website URL'] != '',
            df_final.iloc[idx]['Linkedin URL'] != '',
            df_final.iloc[idx]['Careers Page URL'] != '',
            df_final.iloc[idx]['Job listings page URL'] != ''
        ])
        if has_urls:
            companies_with_urls += 1
        
        has_jobs = any([
            df_final.iloc[idx]['job post1 URL'] != '',
            df_final.iloc[idx]['job post2 URL'] != '',
            df_final.iloc[idx]['job post3 URL'] != ''
        ])
        if has_jobs:
            companies_with_jobs += 1
    
    print(f"✅ Companies with URL data: {companies_with_urls}")
    print(f"💼 Companies with job postings: {companies_with_jobs}")
    print(f"💾 Output saved to: {output_file}")
    print("="*60)
    
    # Display sample results in the requested format
    print("\nSAMPLE OUTPUT (First 3 companies):")
    print("="*60)
    
    for idx in range(min(3, len(df_final))):
        row = df_final.iloc[idx]
        print(f"\nCompany {idx+1}: {row['Company Name']}")
        print(f"Description: {row['Company Description'][:100]}...")
        print(f"Website: {row['Website URL']}")
        print(f"LinkedIn: {row['Linkedin URL']}")
        print(f"Careers: {row['Careers Page URL']}")
        print(f"Jobs: {row['Job listings page URL']}")
        print(f"Job 1: {row['job post1 title']} - {row['job post1 URL']}")
        print(f"Job 2: {row['job post2 title']} - {row['job post2 URL']}")
        print(f"Job 3: {row['job post3 title']} - {row['job post3 URL']}")

if __name__ == "__main__":
    asyncio.run(main())