# Data Formatter - Convert existing data to requested format
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for data access
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def format_existing_data():
    """Convert existing data to the exact format requested"""
    
    try:
        # Read the existing enriched data
        input_file = project_root / "output" / "Data_enriched_final.xlsx"
        df = pd.read_excel(input_file, sheet_name='Data')
        print(f"Loaded {len(df)} companies from existing data")
        
        # Define the exact columns in the requested order
        target_columns = [
            'Company Name', 'Company Description', 'Website URL', 'Linkedin URL', 
            'Careers Page URL', 'Job listings page URL', 'job post1 URL', 'job post1 title',
            'job post2 URL', 'job post2 title', 'job post3 URL', 'job post3 title'
        ]
        
        # Create new dataframe with exact columns needed
        df_formatted = pd.DataFrame()
        
        for col in target_columns:
            if col in df.columns:
                df_formatted[col] = df[col]
            else:
                # Handle missing columns
                if col == 'Company Description' and 'Company Description' in df.columns:
                    df_formatted[col] = df['Company Description']
                elif col == 'Job listings page URL' and 'Jobs Listings Page URL' in df.columns:
                    df_formatted[col] = df['Jobs Listings Page URL']
                else:
                    df_formatted[col] = ''
        
        # Clean up the data
        df_formatted = df_formatted.fillna('')
        
        # Replace 'nan' strings with empty strings
        for col in df_formatted.columns:
            df_formatted[col] = df_formatted[col].astype(str).replace('nan', '')
        
        # Save to new file
        output_file = project_root / "output" / "Data_formatted_final.xlsx"
        df_formatted.to_excel(output_file, index=False)
        
        print(f"\n" + "="*60)
        print("DATA FORMATTING COMPLETED")
        print("="*60)
        print(f"📊 Total companies: {len(df_formatted)}")
        
        # Count companies with data
        companies_with_urls = 0
        companies_with_jobs = 0
        
        for idx in range(len(df_formatted)):
            has_urls = any([
                df_formatted.iloc[idx]['Website URL'] != '',
                df_formatted.iloc[idx]['Linkedin URL'] != '',
                df_formatted.iloc[idx]['Careers Page URL'] != '',
                df_formatted.iloc[idx]['Job listings page URL'] != ''
            ])
            if has_urls:
                companies_with_urls += 1
            
            has_jobs = any([
                df_formatted.iloc[idx]['job post1 URL'] != '',
                df_formatted.iloc[idx]['job post2 URL'] != '',
                df_formatted.iloc[idx]['job post3 URL'] != ''
            ])
            if has_jobs:
                companies_with_jobs += 1
        
        print(f"✅ Companies with URL data: {companies_with_urls}")
        print(f"💼 Companies with job postings: {companies_with_jobs}")
        print(f"💾 Output saved to: {output_file}")
        print("="*60)
        
        # Display first few companies in the exact requested format
        print("\nDATA IN REQUESTED FORMAT:")
        print("="*60)
        
        # Create a sample showing exact format
        sample_df = df_formatted.head(3)
        
        for idx, row in sample_df.iterrows():
            print(f"\nCompany: {row['Company Name']}")
            print(f"Description: {row['Company Description']}")
            print(f"Website URL: {row['Website URL']}")
            print(f"LinkedIn URL: {row['Linkedin URL']}")
            print(f"Careers Page URL: {row['Careers Page URL']}")
            print(f"Job listings page URL: {row['Job listings page URL']}")
            print(f"Job post1 URL: {row['job post1 URL']}")
            print(f"Job post1 title: {row['job post1 title']}")
            print(f"Job post2 URL: {row['job post2 URL']}")
            print(f"Job post2 title: {row['job post2 title']}")
            print(f"Job post3 URL: {row['job post3 URL']}")
            print(f"Job post3 title: {row['job post3 title']}")
            print("-" * 40)
        
        return df_formatted
        
    except Exception as e:
        print(f"Error formatting data: {e}")
        return None

def create_csv_format():
    """Create a CSV with the exact header format requested"""
    try:
        input_file = project_root / "output" / "Data_formatted_final.xlsx"
        df = pd.read_excel(input_file)
        
        # Save as CSV for easier copying
        csv_file = project_root / "output" / "Data_formatted_final.csv"
        df.to_csv(csv_file, index=False)
        print(f"Also saved as CSV format: {csv_file}")
        
        # Print the first few rows in tab-separated format like the example
        print("\nFIRST 3 ROWS IN TAB-SEPARATED FORMAT:")
        print("="*60)
        
        # Header
        headers = [
            "Company Name", "Company Description", "Website URL", "Linkedin URL", 
            "Careers Page URL", "Job listings page URL", "job post1 URL", "job post1 title",
            "job post2 URL", "job post2 title", "job post3 URL", "job post3 title"
        ]
        print("\t".join(headers))
        
        # First 3 rows
        for idx in range(min(3, len(df))):
            row = df.iloc[idx]
            row_data = []
            for col in headers:
                value = str(row[col]) if row[col] != '' else ''
                row_data.append(value)
            print("\t".join(row_data))
            
    except Exception as e:
        print(f"Error creating CSV format: {e}")

if __name__ == "__main__":
    df_result = format_existing_data()
    if df_result is not None:
        create_csv_format()