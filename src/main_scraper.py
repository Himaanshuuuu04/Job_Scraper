# Complete Data Enrichment and Job Scraping Script
import pandas as pd
import asyncio
from datetime import datetime
import requests
from urllib.parse import urlparse
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

async def main():
    """Main function to orchestrate the entire data enrichment and job scraping process"""
    
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

    # Prepare new columns for company data
    df['Website URL'] = ''
    df['Linkedin URL'] = ''
    df['Careers Page URL'] = ''
    df['Jobs Listings Page URL'] = ''
    df['Data Quality Score'] = 0  # Score out of 4 (website, linkedin, careers, jobs)

    # Initialize browser manager and job scraper with controlled settings
    browser_manager = BrowserManager(max_concurrent_tabs=3, headless=True)  # Use headless mode to avoid multiple windows
    job_scraper = JobScraper(browser_manager, max_concurrent_scrapes=2)  # Limit concurrent operations
    all_jobs = []
    
    try:
        await browser_manager.initialize()
        print("Browser initialized successfully!")
        
        print("Phase 1: Enriching company data...")
        # Process only first 6 companies for basic enrichment
        max_companies = 6
        for idx, row in df.iterrows():
            if idx >= max_companies:
                print(f"Reached company limit of {max_companies}!")
                break
            if job_scraper.has_reached_limit():
                print("Reached 200 job postings limit!")
                break
                
            print(f"Processing company {idx+1}/{max_companies}: {row['Company Name']}")
            company = str(row['Company Name'])
            desc = str(row['Company Description'])
            
            # Create optimized search queries for better targeting
            # Extract key industry keywords from description
            industry_keywords = extract_industry_keywords(desc)
            
            # Build DuckDuckGo-optimized search queries
            try:
                search_queries = [
                    # Simple company name search for official website
                    f'{company}',
                    
                    # LinkedIn company page search
                    f'{company} linkedin company',
                    
                    # Careers page searches - multiple variations
                    f'{company} careers',
                    f'{company} jobs',
                    f'{company} careers page',
                    f'{company} employment opportunities',
                    
                    # Job platform specific searches (more direct)
                    f'{company} lever jobs',
                    f'{company} greenhouse careers',
                    f'{company} zoho recruit',
                    f'{company} smartrecruiters',
                    f'{company} workday jobs',
                    
                    # Alternative job listing searches
                    f'{company} current openings',
                    f'{company} job openings',
                    f'{company} hiring now',
                    f'{company} apply jobs'
                ]
                
                # Use the enhanced search with company context for better filtering
                all_links = await browser_manager.search_multiple(search_queries, company)
                links = all_links  # Already deduplicated in search_multiple
                
                quality_score = 0
                
                # Assign links to columns with DuckDuckGo-optimized categorization
                for link in links:
                    link_lower = link.lower()
                    
                    # Priority 1: Job listing platforms (highest priority) - more flexible matching
                    job_platforms = ['lever.co', 'greenhouse.io', 'zohorecruit.com', 'zoho.recruit', 'smartrecruiters.com', 'workday.com', 'bamboohr.com', 'jobvite.com', 'icims.com']
                    if any(platform in link_lower for platform in job_platforms) and not df.at[idx, 'Jobs Listings Page URL']:
                        df.at[idx, 'Jobs Listings Page URL'] = link
                        quality_score += 1
                        continue
                    
                    # Priority 2: LinkedIn company pages - more flexible matching
                    if ('linkedin.com' in link_lower and ('company' in link_lower or '/in/' in link_lower)) and not df.at[idx, 'Linkedin URL']:
                        df.at[idx, 'Linkedin URL'] = link
                        quality_score += 1
                        continue
                    
                    # Priority 3: Careers pages - broader matching
                    career_keywords = ['careers', 'jobs', 'employment', 'opportunities', 'hiring', 'openings', 'join-us', 'work-with-us']
                    if any(keyword in link_lower for keyword in career_keywords) and not df.at[idx, 'Careers Page URL']:
                        # Exclude generic job sites but be less restrictive
                        excluded_job_sites = ['glassdoor.com', 'indeed.com', 'monster.com', 'ziprecruiter.com', 'simplyhired.com']
                        if not any(site in link_lower for site in excluded_job_sites):
                            # Also exclude if it's already categorized as a job platform
                            if not any(platform in link_lower for platform in job_platforms):
                                df.at[idx, 'Careers Page URL'] = link
                                quality_score += 1
                                continue
                    
                    # Priority 4: Company websites (official domains) - more flexible
                    if not df.at[idx, 'Website URL']:
                        # Exclude social media and generic sites
                        excluded_domains = ['linkedin.com', 'facebook.com', 'twitter.com', 'youtube.com', 'instagram.com', 
                                          'glassdoor.com', 'indeed.com', 'monster.com', 'ziprecruiter.com', 'wikipedia.org',
                                          'crunchbase.com', 'bloomberg.com', 'reuters.com']
                        
                        if not any(excluded in link_lower for excluded in excluded_domains):
                            # More flexible company name matching
                            company_clean = company.lower().replace(' ', '').replace('-', '').replace('_', '').replace('.', '')[:8]
                            link_clean = link_lower.replace('https://', '').replace('http://', '').replace('www.', '').replace('-', '').replace('_', '')
                            
                            # Check if company name appears in domain or if it's a .com/.org domain
                            if company_clean in link_clean or any(tld in link for tld in ['.com', '.org', '.net']) and len(link_clean.split('/')[0]) < 50:
                                df.at[idx, 'Website URL'] = link
                                quality_score += 1
                
                df.at[idx, 'Data Quality Score'] = quality_score
                        
            except Exception as e:
                print(f"Error processing {company}: {e}")
        
        print("\nPhase 2: Scraping job postings...")
        # Process companies for job scraping concurrently
        df_limited = df.head(max_companies)
        companies_with_jobs = df_limited[df_limited['Jobs Listings Page URL'] != ''].copy()
        companies_with_careers = df_limited[(df_limited['Careers Page URL'] != '') & (df_limited['Jobs Listings Page URL'] == '')].copy()
        
        # Prepare URLs for concurrent scraping
        urls_to_scrape = []
        
        # Add job listings pages first (higher priority)
        for idx, row in companies_with_jobs.iterrows():
            if len(urls_to_scrape) * job_scraper.max_jobs_per_company >= job_scraper.max_total_jobs:
                break
            company_name = str(row['Company Name'])
            jobs_url = row['Jobs Listings Page URL']
            urls_to_scrape.append((company_name, jobs_url, "jobs"))
        
        # Add careers pages
        for idx, row in companies_with_careers.iterrows():
            if len(urls_to_scrape) * job_scraper.max_jobs_per_company >= job_scraper.max_total_jobs:
                break
            company_name = str(row['Company Name'])
            careers_url = row['Careers Page URL']
            urls_to_scrape.append((company_name, careers_url, "careers"))
        
        # Scrape all URLs concurrently
        if urls_to_scrape:
            print(f"Scraping {len(urls_to_scrape)} URLs concurrently...")
            all_jobs = await job_scraper.scrape_multiple_urls(urls_to_scrape)
        else:
            all_jobs = []
        
        print(f"\nTotal jobs scraped: {len(all_jobs)}")
        
    finally:
        # Clean up scraper tabs first, then close browser
        await job_scraper.cleanup_scraper_tabs()
        await browser_manager.close()
        print("Browser closed successfully!")
    
    # Create comprehensive Excel output
    create_final_excel_output(df, all_jobs)

def validate_urls(df):
    """Validate URLs and update data quality"""
    print("Validating URLs...")
    
    url_columns = ['Website URL', 'Linkedin URL', 'Careers Page URL', 'Jobs Listings Page URL']
    
    for idx, row in df.iterrows():
        working_urls = 0
        for col in url_columns:
            url = row[col]
            if url and url != '':
                try:
                    response = requests.head(url, timeout=10, allow_redirects=True)
                    if response.status_code < 400:
                        working_urls += 1
                    else:
                        print(f"Dead link found for {row['Company Name']}: {url}")
                        df.at[idx, col] = ''  # Remove dead links
                except:
                    print(f"Cannot validate link for {row['Company Name']}: {url}")
                    # Keep the link but note the validation issue
        
        # Update quality score based on working URLs
        df.at[idx, 'Validated URL Count'] = working_urls

def create_final_excel_output(companies_df, jobs_list):
    """Create the final Excel file with proper structure"""
    
    print("Creating final Excel output...")
    
    # Validation step
    validate_urls(companies_df)
    
    # Create jobs DataFrame
    jobs_df = pd.DataFrame(jobs_list)
    
    # Create summary statistics (only for processed companies)
    total_companies = min(len(companies_df), 6)  # Limited to 6 companies
    companies_with_data = len(companies_df.head(6)[companies_df.head(6)['Data Quality Score'] > 0])
    companies_with_jobs = len(jobs_df['company_name'].unique()) if not jobs_df.empty else 0
    total_jobs = len(jobs_df)
    
    # Create methodology text
    methodology_text = f"""
DATA ENRICHMENT AND JOB SCRAPING METHODOLOGY

1. APPROACH OVERVIEW:
   - Automated web scraping using Playwright browser automation
   - DuckDuckGo search for finding company information
   - Targeted scraping of job boards and career pages
   - Data validation and quality scoring

2. TOOLS USED:
   - Python with Playwright for browser automation
   - playwright-stealth for avoiding detection
   - Pandas for data manipulation
   - Custom scrapers for different job platforms

3. DATA SOURCES:
   - Company websites (official domains)
   - LinkedIn company pages
   - Career pages and job listing platforms
   - Supported platforms: Lever, Greenhouse, Zoho Recruit, SmartRecruiters, Workday

4. PROCESS FLOW:
   Step 1: Load company data from Excel
   Step 2: Search for company URLs (website, LinkedIn, careers)
   Step 3: Identify job listing platforms
   Step 4: Scrape job postings (max 3 per company, 200 total)
   Step 5: Validate URLs and clean data
   Step 6: Export to structured Excel format

5. DATA QUALITY MEASURES:
   - URL validation with HTTP requests
   - Duplicate removal
   - Platform-specific parsing
   - Quality scoring (0-4 scale)

6. STATISTICS:
   - Total companies processed: {total_companies}
   - Companies with enriched data: {companies_with_data}
   - Companies with job postings: {companies_with_jobs}
   - Total job postings collected: {total_jobs}
   - Success rate: {(companies_with_data/total_companies*100):.1f}%

7. LIMITATIONS:
   - Some websites may block automated scraping
   - Job posting dates not always available
   - Limited to 200 total job postings as per requirements
   - Some career pages may require JavaScript rendering

8. DATE OF EXECUTION: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    # Write to Excel with multiple sheets
    output_file = project_root / "output" / "Data_enriched_final.xlsx"
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Data sheet with company information
        companies_df.to_excel(writer, sheet_name='Data', index=False)
        
        # Jobs sheet with job postings
        if not jobs_df.empty:
            jobs_df.to_excel(writer, sheet_name='Job_Postings', index=False)
        
        # Methodology sheet
        methodology_df = pd.DataFrame({'Methodology': [methodology_text]})
        methodology_df.to_excel(writer, sheet_name='Methodology', index=False)
        
        # Summary statistics
        summary_data = {
            'Metric': [
                'Total Companies', 'Companies with Data', 'Companies with Jobs', 
                'Total Job Postings', 'Success Rate (%)', 'Execution Date'
            ],
            'Value': [
                total_companies, companies_with_data, companies_with_jobs,
                total_jobs, f"{(companies_with_data/total_companies*100):.1f}%",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    print("\n" + "="*50)
    print("FINAL RESULTS SUMMARY")
    print("="*50)
    print(f"📊 Total companies processed: {total_companies}")
    print(f"✅ Companies with enriched data: {companies_with_data}")
    print(f"💼 Companies with job postings: {companies_with_jobs}")
    print(f"🎯 Total job postings collected: {total_jobs}")
    print(f"📈 Success rate: {(companies_with_data/total_companies*100):.1f}%")
    print(f"💾 Output saved to: {output_file}")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())