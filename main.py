#!/usr/bin/env python3
"""
Company Data Enrichment and Job Scraping Tool
Main entry point for the project

This script provides easy access to all the project's functionality:
- Company data enrichment
- Job posting scraping  
- Data formatting and export

Usage:
    python main.py --help                    # Show all options
    python main.py --enrich                  # Run URL enrichment only
    python main.py --scrape                  # Run full enrichment + job scraping
    python main.py --format                  # Format existing data
    python main.py --example                 # Generate example output
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def print_banner():
    """Print project banner"""
    print("=" * 70)
    print("🚀 COMPANY DATA ENRICHMENT & JOB SCRAPING TOOL")
    print("=" * 70)
    print("📁 Project Structure:")
    print("   ├── src/           # Core scraping scripts")
    print("   ├── data/          # Input data files")
    print("   ├── output/        # Generated output files")
    print("   ├── docs/          # Documentation")
    print("   ├── examples/      # Example scripts")
    print("   └── .venv/         # Python virtual environment")
    print("=" * 70)

async def run_enrichment():
    """Run URL enrichment only"""
    print("🔍 Running URL enrichment...")
    try:
        from enricher import process_companies
        await process_companies()
        print("✅ URL enrichment completed!")
    except Exception as e:
        print(f"❌ Error during enrichment: {e}")

async def run_full_scraping():
    """Run full enrichment + job scraping"""
    print("🎯 Running full data enrichment and job scraping...")
    try:
        from improved_scraper import main
        await main()
        print("✅ Full scraping completed!")
    except Exception as e:
        print(f"❌ Error during scraping: {e}")

def run_formatting():
    """Format existing data"""
    print("📊 Formatting existing data...")
    try:
        from data_formatter import format_existing_data, create_csv_format
        df_result = format_existing_data()
        if df_result is not None:
            create_csv_format()
        print("✅ Data formatting completed!")
    except Exception as e:
        print(f"❌ Error during formatting: {e}")

def run_example():
    """Generate example output"""
    print("📝 Generating example output...")
    try:
        import sys
        sys.path.insert(0, str(project_root / "examples"))
        exec(open(project_root / "examples" / "perfect_format_example.py").read())
        print("✅ Example generation completed!")
    except Exception as e:
        print(f"❌ Error generating example: {e}")

def show_project_status():
    """Show current project status"""
    print("📋 PROJECT STATUS:")
    print("-" * 40)
    
    # Check for data files
    data_dir = project_root / "data"
    output_dir = project_root / "output"
    
    print(f"📂 Data directory: {data_dir.exists()}")
    if data_dir.exists():
        data_files = list(data_dir.glob("*.xlsx"))
        print(f"   Input files: {len(data_files)}")
        for file in data_files:
            print(f"   - {file.name}")
    
    print(f"📂 Output directory: {output_dir.exists()}")
    if output_dir.exists():
        output_files = list(output_dir.glob("*.xlsx")) + list(output_dir.glob("*.csv"))
        print(f"   Output files: {len(output_files)}")
        for file in output_files[:5]:  # Show first 5
            print(f"   - {file.name}")
        if len(output_files) > 5:
            print(f"   ... and {len(output_files) - 5} more")
    
    print("-" * 40)

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Company Data Enrichment and Job Scraping Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py --enrich          # Run URL enrichment only
    python main.py --scrape          # Run full enrichment + job scraping
    python main.py --format          # Format existing data
    python main.py --example         # Generate example output
    python main.py --status          # Show project status
        """
    )
    
    parser.add_argument("--enrich", action="store_true", 
                       help="Run URL enrichment only")
    parser.add_argument("--scrape", action="store_true", 
                       help="Run full enrichment and job scraping")
    parser.add_argument("--format", action="store_true", 
                       help="Format existing data to requested format")
    parser.add_argument("--example", action="store_true", 
                       help="Generate example output")
    parser.add_argument("--status", action="store_true", 
                       help="Show project status")
    
    args = parser.parse_args()
    
    print_banner()
    
    if args.status:
        show_project_status()
        return
    
    if args.enrich:
        await run_enrichment()
    elif args.scrape:
        await run_full_scraping()
    elif args.format:
        run_formatting()
    elif args.example:
        run_example()
    else:
        print("Please specify an action. Use --help for available options.")
        print("\nQuick start:")
        print("  python main.py --status     # Check project status")
        print("  python main.py --scrape     # Run full scraping")
        print("  python main.py --format     # Format existing data")

if __name__ == "__main__":
    asyncio.run(main())