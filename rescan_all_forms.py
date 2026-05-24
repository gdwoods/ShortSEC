"""
Comprehensive Re-scan Script: Scan all form types to catch missing filings

This script performs a thorough scan of all relevant form types with increased counts
to catch filings that may have been missed due to:
1. New form types being added (424B3, F-1, F-3, etc.)
2. Limited count in previous scans
3. Recent filings that weren't in the feed at the time

The script will:
- Scan each form type with a large count (200 per form)
- Process and analyze all filings
- Save to Supabase (deduplication handled automatically)
- Show summary of new filings found
"""

import sys
from typing import List, Dict, Set
import pandas as pd
from datetime import datetime

from config import RELEVANT_FORM_TYPES
from universe_builder import build_or_load_universe
from filing_scanner import scan_filings_by_form_type, enrich_filings_with_tickers
from analyzer import analyze_filings
from filing_parser import parse_filing_details
from main import save_alerts
from price_filter import filter_filings_by_price
from supabase_storage import init_supabase


def get_existing_filing_keys(client) -> Set[str]:
    """
    Get set of existing filing keys (ticker + date + form_type) from database.
    Used to identify truly new filings.
    """
    if not client:
        return set()
    
    try:
        result = client.table("sec_filing_alerts").select("ticker, date, form_type").execute()
        keys = set()
        for row in result.data:
            key = f"{row.get('ticker', '').upper()}_{row.get('date', '')}_{row.get('form_type', '')}"
            keys.add(key)
        return keys
    except Exception as e:
        print(f"[Rescan] Warning: Could not fetch existing filings: {e}")
        return set()


def rescan_all_forms(max_per_form: int = 200, max_price: float = None) -> List[Dict]:
    """
    Comprehensive re-scan of all form types.
    
    Args:
        max_per_form: Maximum filings to fetch per form type (default: 200)
        max_price: Optional price filter (e.g., 20.0 for stocks under $20)
        
    Returns:
        List of all found filing dictionaries
    """
    print("=" * 80)
    print("COMPREHENSIVE RE-SCAN: All Form Types")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Form types to scan: {len(RELEVANT_FORM_TYPES)}")
    print(f"Max filings per form: {max_per_form}")
    print(f"Form types: {', '.join(RELEVANT_FORM_TYPES)}")
    print()
    
    # Load universe
    print("[Rescan] Step 1: Loading company universe...")
    universe_df = build_or_load_universe(force_refresh=False)
    if universe_df is None:
        print("[Rescan] ❌ Failed to load universe")
        return []
    print(f"[Rescan] ✓ Loaded universe with {len(universe_df)} companies\n")
    
    # Get existing filings for comparison
    print("[Rescan] Step 2: Checking existing filings in database...")
    client = init_supabase()
    existing_keys = get_existing_filing_keys(client)
    print(f"[Rescan] ✓ Found {len(existing_keys)} existing filings in database\n")
    
    # Scan each form type
    print("[Rescan] Step 3: Scanning all form types...")
    print("-" * 80)
    all_filings = []
    existing_links = set()  # Deduplicate by link
    
    for i, form_type in enumerate(RELEVANT_FORM_TYPES, 1):
        print(f"[Rescan] [{i}/{len(RELEVANT_FORM_TYPES)}] Scanning {form_type}...")
        
        try:
            filings = scan_filings_by_form_type(form_type, count=max_per_form, days_back=None)
            
            if filings:
                # Enrich with ticker symbols
                enriched = enrich_filings_with_tickers(filings, universe_df)
                
                # Deduplicate by link
                new_filings = []
                for filing in enriched:
                    link = filing.get("link", "")
                    if link and link not in existing_links:
                        new_filings.append(filing)
                        existing_links.add(link)
                
                all_filings.extend(new_filings)
                print(f"  ✓ Found {len(new_filings)} new {form_type} filings (total: {len(all_filings)})")
            else:
                print(f"  ⚠️  No {form_type} filings found")
        except Exception as e:
            print(f"  ❌ Error scanning {form_type}: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print(f"[Rescan] ✓ Total filings found: {len(all_filings)}\n")
    
    if not all_filings:
        print("[Rescan] ⚠️  No new filings found")
        return []
    
    # Filter by price if specified
    if max_price:
        print(f"[Rescan] Step 4: Filtering by price (max: ${max_price:.2f})...")
        initial_count = len(all_filings)
        all_filings = filter_filings_by_price(all_filings, max_price=max_price, fetch_prices=True)
        filtered_count = initial_count - len(all_filings)
        print(f"[Rescan] ✓ Filtered out {filtered_count} filings (remaining: {len(all_filings)})\n")
    
    # Analyze filings
    print("[Rescan] Step 5: Analyzing filings for red flags...")
    analyzed_filings = analyze_filings(all_filings)
    print(f"[Rescan] ✓ Analysis complete\n")
    
    # Parse filing details
    print("[Rescan] Step 6: Parsing filing details...")
    parsed_filings = []
    for i, filing in enumerate(analyzed_filings, 1):
        if i % 10 == 0:
            print(f"  Processing {i}/{len(analyzed_filings)}...")
        details = parse_filing_details(filing, max_price=None)  # Already filtered
        filing.update(details)
        parsed_filings.append(filing)
    print(f"[Rescan] ✓ Parsed details for {len(parsed_filings)} filings\n")
    
    # Identify truly new filings (not in database)
    print("[Rescan] Step 7: Identifying new filings...")
    new_filings = []
    for filing in parsed_filings:
        ticker = filing.get("ticker", "").upper()
        if ticker == "UNKNOWN":
            continue
        
        date_str = filing.get("pubDate") or filing.get("date", "")
        form_type = filing.get("form_type", "")
        
        if date_str and form_type:
            try:
                from dateutil import parser
                date_obj = parser.parse(date_str)
                date_formatted = date_obj.strftime("%Y-%m-%d")
                key = f"{ticker}_{date_formatted}_{form_type}"
                
                if key not in existing_keys:
                    new_filings.append(filing)
            except Exception:
                # If date parsing fails, include it (better to include than exclude)
                new_filings.append(filing)
        else:
            # If missing date/form_type, include it
            new_filings.append(filing)
    
    print(f"[Rescan] ✓ Found {len(new_filings)} truly new filings (not in database)\n")
    
    # Show summary
    print("=" * 80)
    print("RE-SCAN SUMMARY")
    print("=" * 80)
    print(f"Total filings scanned: {len(all_filings)}")
    print(f"New filings found: {len(new_filings)}")
    print(f"Form type breakdown:")
    
    form_type_counts = {}
    for filing in new_filings:
        form_type = filing.get("form_type", "UNKNOWN")
        form_type_counts[form_type] = form_type_counts.get(form_type, 0) + 1
    
    for form_type, count in sorted(form_type_counts.items(), key=lambda x: -x[1]):
        print(f"  {form_type}: {count}")
    
    if new_filings:
        print(f"\nSample new filings:")
        for i, filing in enumerate(new_filings[:10], 1):
            ticker = filing.get("ticker", "UNKNOWN")
            form_type = filing.get("form_type", "UNKNOWN")
            date = filing.get("pubDate") or filing.get("date", "N/A")
            risk_score = filing.get("risk_score", 0)
            title = (filing.get("title", "N/A") or "N/A")[:50]
            print(f"  {i}. {ticker} ({form_type}) - {date} - Risk: {risk_score} - {title}")
    
    return new_filings


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Comprehensive re-scan of all form types")
    parser.add_argument("--max-per-form", type=int, default=200, help="Max filings per form type (default: 200)")
    parser.add_argument("--max-price", type=float, default=None, help="Filter to stocks under this price (e.g., 20.0)")
    parser.add_argument("--save", action="store_true", help="Save results to database/CSV")
    
    args = parser.parse_args()
    
    # Run comprehensive scan
    new_filings = rescan_all_forms(max_per_form=args.max_per_form, max_price=args.max_price)
    
    if not new_filings:
        print("\n⚠️  No new filings found in this scan")
        sys.exit(0)
    
    # Save if requested
    if args.save:
        print("\n" + "=" * 80)
        print("SAVING RESULTS")
        print("=" * 80)
        success = save_alerts(new_filings)
        if success:
            # Check if it actually saved to Supabase or CSV
            client = init_supabase()
            if client:
                print(f"\n✅ Successfully saved {len(new_filings)} new filings to Supabase database")
            else:
                print(f"\n⚠️  Saved {len(new_filings)} new filings to CSV (Supabase not configured)")
                print(f"   CSV location: data/dilution_alerts.csv")
                print(f"   To import to Supabase, run: python3 import_csv_to_supabase.py")
        else:
            print(f"\n❌ Failed to save results")
            sys.exit(1)
    else:
        print("\n💡 Tip: Run with --save to save results to database")
    
    print(f"\n✅ Re-scan complete: {len(new_filings)} new filings found")
