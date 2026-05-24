"""
Populate Country for Companies with Existing Alerts

This script backfills country information for companies that already have
filings in the sec_filing_alerts table.

Usage:
    python3 populate_country_for_existing_alerts.py
"""

import os
import sys
import time
import requests
from typing import Optional, Dict, Set
from supabase_storage import init_supabase

# SEC API configuration
SEC_BASE_URL = "https://www.sec.gov"
SEC_DATA_BASE = "https://data.sec.gov"

# SEC headers for API requests
SEC_HEADERS = {
    "User-Agent": "SEC-EDGAR-Scraper (garthwoods@gmail.com)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip, deflate"
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


def fetch_company_info(cik: str, retries: int = 3) -> Optional[Dict]:
    """
    Fetch company information from SEC submissions API.
    
    Args:
        cik: Company CIK (with or without leading zeros)
        retries: Number of retry attempts
        
    Returns:
        Dictionary with title and country, or None if not found
    """
    # Normalize CIK (remove leading zeros)
    cik_numeric = str(cik).lstrip("0")
    if not cik_numeric:
        return None
    
    # Construct submissions API URL
    submissions_url = f"{SEC_DATA_BASE}/submissions/CIK{cik_numeric.zfill(10)}.json"
    
    for attempt in range(retries):
        try:
            time.sleep(0.1)  # Rate limiting: SEC requires 10 requests/second max
            response = requests.get(submissions_url, headers=SEC_HEADERS, timeout=30)
            
            # Debug: print status for first few attempts
            if attempt == 0 and int(cik) % 50 == 0:  # Print every 50th to avoid spam
                print(f"    [Debug] Status {response.status_code} for CIK {cik}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract company name
                name = data.get("name", "")
                
                # Extract country from addresses
                addresses = data.get("addresses", {})
                business_address = addresses.get("business")
                mailing_address = addresses.get("mailing")
                
                country = None
                if business_address:
                    country = normalize_country(business_address)
                if not country and mailing_address:
                    country = normalize_country(mailing_address)
                
                return {
                    "title": name,
                    "country": country
                }
                
            elif response.status_code == 404:
                # Company not found or no submissions
                if attempt == retries - 1:
                    # Only print on last attempt to reduce noise
                    pass
                return None
            elif response.status_code == 429:
                # Rate limited - wait longer
                wait_time = (attempt + 1) * 2
                print(f"[Rate Limited] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                # Log unexpected status codes on last attempt
                if attempt == retries - 1:
                    print(f"[Error] Unexpected status {response.status_code} for CIK {cik}")
                if attempt < retries - 1:
                    time.sleep(1)
                    
        except requests.RequestException as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                # Print error for debugging (only on last attempt to reduce noise)
                if int(cik) % 50 == 0:  # Only print every 50th error to avoid spam
                    print(f"    [Debug] Request exception for CIK {cik}: {type(e).__name__}")
    
    return None


def get_cik_from_ticker(ticker: str, client) -> Optional[str]:
    """
    Get CIK for a ticker from SEC company_tickers.json.
    
    Args:
        ticker: Stock ticker symbol
        client: Supabase client (not used, but kept for consistency)
        
    Returns:
        CIK string, or None if not found
    """
    try:
        time.sleep(0.1)
        response = requests.get(
            f"{SEC_BASE_URL}/files/company_tickers.json",
            headers=SEC_HEADERS,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            for entry in data.values():
                if entry.get("ticker", "").strip().upper() == ticker.upper():
                    return str(entry.get("cik_str", ""))
    except Exception as e:
        print(f"[Error] Failed to fetch CIK for ticker {ticker}: {e}")
    
    return None


def populate_country_for_existing_alerts(dry_run: bool = False):
    """
    Populate country information for companies that have alerts.
    
    Args:
        dry_run: If True, don't save to database (just print what would be saved)
    """
    # Initialize Supabase
    client = init_supabase()
    if not client:
        print("[Error] Failed to initialize Supabase client")
        print("[Error] Make sure SUPABASE_URL and SUPABASE_ANON_KEY are set")
        return
    
    # Get all unique tickers from alerts table
    print("[Fetching] Loading unique tickers from alerts table...")
    try:
        response = client.table('sec_filing_alerts').select('ticker').execute()
        tickers = set()
        for row in response.data:
            ticker = row.get('ticker')
            if ticker:
                tickers.add(ticker.upper())
        
        print(f"[Fetching] Found {len(tickers)} unique tickers with alerts")
    except Exception as e:
        print(f"[Error] Failed to fetch tickers: {e}")
        return
    
    if not tickers:
        print("[Warning] No tickers found in alerts table")
        return
    
    # Check which tickers already have country info
    print("[Checking] Checking which companies already have country info...")
    try:
        response = client.table('company_universe').select('ticker, country').execute()
        existing_countries = {row['ticker'].upper(): row.get('country') for row in response.data if row.get('ticker')}
    except Exception as e:
        print(f"[Warning] Could not check existing countries: {e}")
        existing_countries = {}
    
    # Filter to tickers that don't have country yet
    tickers_to_process = [t for t in tickers if not existing_countries.get(t)]
    
    if not tickers_to_process:
        print("[Info] All tickers already have country information")
        return
    
    print(f"[Processing] Processing {len(tickers_to_process)} tickers without country info...")
    
    total_processed = 0
    total_with_country = 0
    total_updated = 0
    
    # Process tickers
    for ticker in sorted(tickers_to_process):
        total_processed += 1
        print(f"[Processing] {total_processed}/{len(tickers_to_process)}: {ticker}")
        
        # Get CIK for this ticker
        cik = get_cik_from_ticker(ticker, client)
        
        if not cik:
            print(f"  [Warning] Could not find CIK for {ticker}")
            continue
        
        # Fetch company info (name and country)
        company_info = fetch_company_info(cik)
        
        if not company_info:
            print(f"  [Warning] Could not fetch info for {ticker} (CIK: {cik})")
            # Still insert record without country
            company_info = {"title": None, "country": None}
        
        if company_info.get("country"):
            total_with_country += 1
        
        # Prepare record for upsert
        record = {
            "cik": cik,
            "ticker": ticker,
            "title": company_info.get("title"),
            "country": company_info.get("country"),
        }
        
        # Save to database
        if not dry_run:
            try:
                client.table('company_universe').upsert([record], on_conflict='cik').execute()
                total_updated += 1
                print(f"  [Saved] {ticker}: {company_info.get('country', 'No country')}")
            except Exception as e:
                print(f"  [Error] Failed to save {ticker}: {e}")
        else:
            print(f"  [Dry Run] Would save {ticker}: {company_info.get('country', 'No country')}")
        
        # Small delay to avoid rate limiting
        if total_processed < len(tickers_to_process):
            time.sleep(0.15)  # ~6-7 requests per second (under SEC limit of 10/sec)
    
    print("\n[Complete] Backfill complete!")
    print(f"  Total processed: {total_processed}")
    print(f"  With country: {total_with_country} ({total_with_country/total_processed*100:.1f}% if total > 0)")
    print(f"  Total saved: {total_updated if not dry_run else 0}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Populate country for companies with existing alerts")
    parser.add_argument("--dry-run", action="store_true", help="Don't save to database, just print what would be saved")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Populate Country for Existing Alerts")
    print("=" * 60)
    
    if args.dry_run:
        print("[Mode] DRY RUN - No changes will be saved to database")
    
    print()
    
    populate_country_for_existing_alerts(dry_run=args.dry_run)
