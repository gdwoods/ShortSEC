"""
Add Missing Company to company_universe

This script adds a specific company (or companies) to the company_universe table
if they exist in SEC data but are missing from the database.

Usage:
    python3 add_missing_company.py NMR
    python3 add_missing_company.py NMR AAPL MSFT  # Multiple tickers
"""

import os
import sys
import time
import requests
from typing import Optional, Dict, List
from supabase_storage import init_supabase

# SEC API configuration
SEC_BASE_URL = "https://www.sec.gov"
SEC_DATA_BASE = "https://data.sec.gov"

SEC_HEADERS = {
    "User-Agent": "SEC-EDGAR-Scraper (garthwoods@gmail.com)",
    "Accept": "application/json",
}


def normalize_country_from_address(address: Dict) -> Optional[str]:
    """Normalize country from SEC address data."""
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
    
    if state_or_country in us_states:
        return "USA"
    if state_or_country_desc:
        return state_or_country_desc
    if state_or_country:
        return state_or_country
    return None


def get_cik_from_ticker(ticker: str) -> Optional[str]:
    """Get CIK for a ticker from SEC company_tickers.json."""
    try:
        time.sleep(0.1)
        response = requests.get(
            f"{SEC_BASE_URL}/files/company_tickers.json",
            headers=SEC_HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            for entry in data.values():
                if entry.get("ticker", "").strip().upper() == ticker.upper():
                    return str(entry.get("cik_str", ""))
    except Exception as e:
        print(f"[Error] Failed to fetch CIK for {ticker}: {e}")
    
    return None


def fetch_company_info(cik: str) -> Optional[Dict]:
    """Fetch company information from SEC submissions API."""
    cik_numeric = str(cik).lstrip("0").zfill(10)
    
    try:
        time.sleep(0.1)
        response = requests.get(
            f"{SEC_DATA_BASE}/submissions/CIK{cik_numeric}.json",
            headers=SEC_HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            name = data.get("name", "")
            addresses = data.get("addresses", {})
            
            business_address = addresses.get("business")
            mailing_address = addresses.get("mailing")
            
            country = None
            if business_address:
                country = normalize_country_from_address(business_address)
            if not country and mailing_address:
                country = normalize_country_from_address(mailing_address)
            
            return {
                "title": name,
                "country": country
            }
    except Exception as e:
        print(f"[Error] Failed to fetch company info for CIK {cik}: {e}")
    
    return None


def add_company_to_universe(ticker: str, client, dry_run: bool = False) -> bool:
    """Add a company to company_universe table."""
    ticker_upper = ticker.upper()
    
    print(f"[Processing] {ticker_upper}")
    
    # Check if already exists
    try:
        response = client.table('company_universe').select('cik, ticker, country').eq('ticker', ticker_upper).execute()
        
        if response.data:
            existing = response.data[0]
            print(f"  [Info] Already exists: CIK={existing.get('cik')}, Country={existing.get('country', 'None')}")
            return False
    except Exception as e:
        print(f"  [Warning] Error checking existing record: {e}")
    
    # Get CIK from SEC
    cik = get_cik_from_ticker(ticker_upper)
    
    if not cik:
        print(f"  [Error] Could not find CIK for {ticker_upper} in SEC data")
        return False
    
    print(f"  [Info] Found CIK: {cik}")
    
    # Fetch company info
    company_info = fetch_company_info(cik)
    
    if company_info:
        print(f"  [Info] Company name: {company_info.get('title', 'N/A')}")
        print(f"  [Info] Country: {company_info.get('country', 'None')}")
    else:
        print(f"  [Warning] Could not fetch company info, will save with minimal data")
        company_info = {"title": None, "country": None}
    
    # Prepare record
    record = {
        "cik": cik,
        "ticker": ticker_upper,
        "title": company_info.get("title"),
        "country": company_info.get("country"),
    }
    
    # Save to database
    if not dry_run:
        try:
            client.table('company_universe').upsert([record], on_conflict='cik').execute()
            print(f"  [Success] Added {ticker_upper} to company_universe")
            return True
        except Exception as e:
            print(f"  [Error] Failed to save: {e}")
            return False
    else:
        print(f"  [Dry Run] Would add: {record}")
        return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 add_missing_company.py <TICKER> [TICKER2] [TICKER3] ...")
        print("Example: python3 add_missing_company.py NMR")
        sys.exit(1)
    
    tickers = [t.upper() for t in sys.argv[1:]]
    dry_run = '--dry-run' in tickers
    if dry_run:
        tickers.remove('--dry-run')
    
    if not tickers:
        print("Error: No tickers provided")
        sys.exit(1)
    
    # Initialize Supabase
    client = init_supabase()
    if not client:
        print("[Error] Failed to initialize Supabase client")
        print("[Error] Make sure SUPABASE_URL and SUPABASE_ANON_KEY are set")
        sys.exit(1)
    
    print("=" * 60)
    print("Add Missing Company to company_universe")
    print("=" * 60)
    
    if dry_run:
        print("[Mode] DRY RUN - No changes will be saved")
    
    print(f"[Processing] {len(tickers)} ticker(s): {', '.join(tickers)}")
    print()
    
    success_count = 0
    for ticker in tickers:
        if add_company_to_universe(ticker, client, dry_run=dry_run):
            success_count += 1
        print()
    
    print(f"[Complete] Processed {len(tickers)} ticker(s), {success_count} added/updated")


if __name__ == "__main__":
    main()
