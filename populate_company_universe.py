"""
Populate Company Universe Table

This script fetches all companies from SEC company_tickers.json and populates
the company_universe table with CIK, ticker, company name, and country information.

Country information is extracted from SEC submissions API (business address).

Usage:
    python3 populate_company_universe.py
"""

import os
import sys
import time
import requests
from typing import Optional, Dict, List
from supabase_storage import init_supabase

# SEC API configuration
SEC_BASE_URL = "https://www.sec.gov"
SEC_COMPANY_TICKERS_URL = f"{SEC_BASE_URL}/files/company_tickers.json"
SEC_SUBMISSIONS_URL_TEMPLATE = f"{SEC_BASE_URL}/cgi-bin/browse-edgar?action=getcompany&CIK={{cik}}&type=&dateb=&owner=exclude&count=1&output=atom"
SEC_API_BASE = f"{SEC_BASE_URL}/data"

# SEC headers for API requests
SEC_HEADERS = {
    "User-Agent": "SEC-EDGAR-Scraper (garthwoods@gmail.com)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate",
    "Host": "www.sec.gov"
}


def normalize_country(address: Dict) -> Optional[str]:
    """
    Normalize country from SEC address data.
    
    Args:
        address: SEC address dictionary with stateOrCountry and stateOrCountryDescription
        
    Returns:
        Normalized country name, or None if not available
    """
    if not address:
        return None
    
    us_states = {
        "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
        "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
        "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
        "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
        "WI", "WY", "DC", "PR"
    }
    
    state_or_country = (address.get("stateOrCountry") or "").strip().upper()
    state_or_country_desc = (address.get("stateOrCountryDescription") or "").strip()
    
    # If it's a US state code, return "USA"
    if state_or_country in us_states:
        return "USA"
    
    # If we have a description, use it
    if state_or_country_desc:
        return state_or_country_desc
    
    # Otherwise use the code (might be a country code)
    if state_or_country:
        return state_or_country
    
    return None


def fetch_company_country(cik: str, retries: int = 3) -> Optional[str]:
    """
    Fetch company country from SEC submissions API.
    
    Args:
        cik: Company CIK (without leading zeros)
        retries: Number of retry attempts
        
    Returns:
        Country name, or None if not found
    """
    # Normalize CIK (remove leading zeros)
    cik_numeric = str(cik).lstrip("0")
    if not cik_numeric:
        return None
    
    # Construct submissions API URL
    submissions_url = f"{SEC_API_BASE}/submissions/CIK{cik_numeric.zfill(10)}.json"
    
    for attempt in range(retries):
        try:
            time.sleep(0.1)  # Rate limiting: SEC requires 10 requests/second max
            response = requests.get(submissions_url, headers=SEC_HEADERS, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                addresses = data.get("addresses", {})
                
                # Try business address first, then mailing address
                business_address = addresses.get("business")
                mailing_address = addresses.get("mailing")
                
                country = None
                if business_address:
                    country = normalize_country(business_address)
                if not country and mailing_address:
                    country = normalize_country(mailing_address)
                
                return country
                
            elif response.status_code == 404:
                # Company not found or no submissions
                return None
            elif response.status_code == 429:
                # Rate limited - wait longer
                wait_time = (attempt + 1) * 2
                print(f"[Rate Limited] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                if attempt < retries - 1:
                    time.sleep(1)
                    
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"[Error] Failed to fetch country for CIK {cik}: {e}")
    
    return None


def fetch_all_companies() -> List[Dict]:
    """
    Fetch all companies from SEC company_tickers.json.
    
    Returns:
        List of company dictionaries with CIK, ticker, and title
    """
    print("[Fetching] Loading company tickers from SEC...")
    
    try:
        time.sleep(0.1)  # Rate limiting
        response = requests.get(SEC_COMPANY_TICKERS_URL, headers=SEC_HEADERS, timeout=30)
        
        if response.status_code != 200:
            print(f"[Error] Failed to fetch company tickers: HTTP {response.status_code}")
            return []
        
        data = response.json()
        companies = []
        
        # The JSON structure is: {"0": {"cik_str": "...", "ticker": "...", "title": "..."}, ...}
        for entry in data.values():
            cik = str(entry.get("cik_str", ""))
            ticker = entry.get("ticker", "").strip().upper()
            title = entry.get("title", "").strip()
            
            if cik and ticker:
                companies.append({
                    "cik": cik,
                    "ticker": ticker,
                    "title": title,
                })
        
        print(f"[Fetching] Loaded {len(companies)} companies from SEC")
        return companies
        
    except Exception as e:
        print(f"[Error] Failed to fetch companies: {e}")
        return []


def populate_company_universe(dry_run: bool = False, limit: Optional[int] = None):
    """
    Populate company_universe table with companies and their countries.
    
    Args:
        dry_run: If True, don't save to database (just print what would be saved)
        limit: Limit number of companies to process (for testing)
    """
    # Initialize Supabase
    client = init_supabase()
    if not client:
        print("[Error] Failed to initialize Supabase client")
        print("[Error] Make sure SUPABASE_URL and SUPABASE_ANON_KEY are set")
        return
    
    # Fetch all companies from SEC
    companies = fetch_all_companies()
    
    if not companies:
        print("[Error] No companies fetched from SEC")
        return
    
    if limit:
        companies = companies[:limit]
        print(f"[Testing] Limiting to first {limit} companies")
    
    print(f"[Processing] Processing {len(companies)} companies...")
    
    # Process companies in batches
    batch_size = 100
    total_processed = 0
    total_with_country = 0
    total_updated = 0
    
    for i in range(0, len(companies), batch_size):
        batch = companies[i:i + batch_size]
        batch_records = []
        
        for company in batch:
            cik = company["cik"]
            ticker = company["ticker"]
            title = company["title"]
            
            # Fetch country from SEC submissions API
            print(f"[Processing] {total_processed + 1}/{len(companies)}: {ticker} (CIK: {cik})")
            country = fetch_company_country(cik)
            
            if country:
                total_with_country += 1
            
            record = {
                "cik": cik,
                "ticker": ticker,
                "title": title,
                "country": country,
            }
            
            batch_records.append(record)
            total_processed += 1
        
        # Save batch to database
        if not dry_run:
            try:
                # Upsert records (insert or update on conflict with cik)
                client.table('company_universe').upsert(batch_records, on_conflict='cik').execute()
                total_updated += len(batch_records)
                print(f"[Saved] Batch {i//batch_size + 1}: Saved {len(batch_records)} companies")
            except Exception as e:
                print(f"[Error] Failed to save batch: {e}")
        else:
            print(f"[Dry Run] Would save batch {i//batch_size + 1}: {len(batch_records)} companies")
            for record in batch_records[:3]:  # Show first 3 as sample
                print(f"  Sample: {record['ticker']} - {record['title']} ({record.get('country', 'No country')})")
        
        # Progress update
        print(f"[Progress] Processed: {total_processed}/{len(companies)}, "
              f"With country: {total_with_country}, Saved: {total_updated}")
        
        # Small delay between batches to avoid rate limiting
        if i + batch_size < len(companies):
            time.sleep(0.5)
    
    print("\n[Complete] Population complete!")
    print(f"  Total processed: {total_processed}")
    print(f"  With country: {total_with_country} ({total_with_country/total_processed*100:.1f}%)")
    print(f"  Total saved: {total_updated if not dry_run else 0}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate company_universe table with SEC data")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to database, just print what would be saved")
    parser.add_argument("--limit", type=int, help="Limit number of companies to process (for testing)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Populate Company Universe Table")
    print("=" * 60)
    
    if args.dry_run:
        print("[Mode] DRY RUN - No changes will be saved to database")
    
    if args.limit:
        print(f"[Mode] TESTING - Limited to {args.limit} companies")
    
    print()
    
    populate_company_universe(dry_run=args.dry_run, limit=args.limit)
