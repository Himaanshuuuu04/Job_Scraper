# Import required modules
import pandas as pd
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for data access
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapper import BrowserManager

# Read the Excel file
data_file = project_root / "data" / "Data.xlsx"
try:
    df = pd.read_excel(data_file)
except FileNotFoundError:
    print(f"Error: {data_file} file not found!")
    exit(1)
except Exception as e:
    print(f"Error reading {data_file}: {e}")
    exit(1)

# Prepare new columns
df['Website URL'] = ''
df['Linkedin URL'] = ''
df['Careers Page URL'] = ''
df['Jobs Listings Page URL'] = ''

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

async def process_companies():
    # Initialize browser manager once with headless mode
    browser_manager = BrowserManager(max_concurrent_tabs=2, headless=True)
    try:
        await browser_manager.initialize()
        print("Browser initialized successfully!")
        
        count = 0
        for idx, row in df.iterrows():
            print("searching for ",str(row['Company Name']))
            company = str(row['Company Name'])
            desc = str(row['Company Description'])
            
            # Create DuckDuckGo-optimized search queries
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
                f'{company} hiring now'
            ]
            
            # Perform all searches using the enhanced browser with company context
            try:
                all_links = await browser_manager.search_multiple(search_queries, company)

                # Links are already deduplicated and filtered by BeautifulSoup
                links = list(set(all_links))
                
                # Assign links to columns with DuckDuckGo-optimized categorization
                for link in links:
                    link_lower = link.lower()
                    
                    # Priority 1: Job listing platforms (highest priority) - more flexible matching
                    job_platforms = ['lever.co', 'greenhouse.io', 'zohorecruit.com', 'zoho.recruit', 'smartrecruiters.com', 'workday.com', 'bamboohr.com', 'jobvite.com', 'icims.com']
                    if any(platform in link_lower for platform in job_platforms) and not df.at[idx, 'Jobs Listings Page URL']:
                        df.at[idx, 'Jobs Listings Page URL'] = link
                        continue
                    
                    # Priority 2: LinkedIn company pages - more flexible matching
                    if ('linkedin.com' in link_lower and ('company' in link_lower or '/in/' in link_lower)) and not df.at[idx, 'Linkedin URL']:
                        df.at[idx, 'Linkedin URL'] = link
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
                        
            except Exception as e:
                print(f"Error processing {company}: {e}")
            
            count += 1
            # Process all companies (remove the break to handle all ~150 companies)
            # if count >= 5:
            #     break
                
    finally:
        # Always close the browser when done
        await browser_manager.close()
        print("Browser closed successfully!")
    
    # Save the enriched data after processing
    try:
        output_file = project_root / "output" / "Data_enriched.xlsx"
        df.to_excel(output_file, index=False)
        print(f"Data enrichment completed successfully! Output saved to {output_file}")
    except Exception as e:
        print(f"Error saving enriched data: {e}")

# Run the async function
asyncio.run(process_companies())
