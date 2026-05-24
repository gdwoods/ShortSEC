"""
Backfill New Fields: Re-parse existing filings to extract new fields

This script re-downloads and re-parses existing filings to extract:
- offering_type
- bank (first underwriter)
- investors
- share_equivalent

It updates existing database records with these fields.
"""

import sys
import time
from typing import List, Dict, Optional
from datetime import datetime
from supabase import Client

from supabase_storage import init_supabase
from filing_parser import parse_filing_details
from config import SEC_REQUEST_DELAY


def backfill_new_fields(
    client: Client,
    table_name: str = "sec_filing_alerts",
    limit: Optional[int] = None,
    dry_run: bool = False
) -> int:
    """
    Backfills new fields (offering_type, bank, investors, share_equivalent) for existing filings.
    
    Args:
        client: Supabase client
        table_name: Table name (default: sec_filing_alerts)
        limit: Optional limit on number of filings to process (None = all)
        dry_run: If True, only show what would be updated without making changes
        
    Returns:
        Number of filings updated
    """
    print("=" * 80)
    print("BACKFILL NEW FIELDS: Re-parsing existing filings")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if dry_run:
        print("⚠️  DRY RUN MODE: No changes will be made")
    print()
    
    try:
        # Fetch filings that need backfilling
        # We'll process filings where at least one of the new fields is NULL
        print("[Backfill] Step 1: Fetching filings that need backfilling...")
        
        # Fetch all filings (we'll filter in Python to check which ones need updates)
        query = client.table(table_name).select('id, ticker, date, form_type, link_to_filing, offering_type, bank, investors, share_equivalent').order('date', desc=True)
        
        if limit:
            query = query.limit(limit)
        
        response = query.execute()
        all_filings = response.data
        
        # Filter to filings that need backfilling (at least one new field is NULL)
        filings_to_process = []
        for filing in all_filings:
            offering_type = filing.get('offering_type')
            bank = filing.get('bank')
            investors = filing.get('investors')
            share_equivalent = filing.get('share_equivalent')
            
            # Process if at least one field is missing
            if not offering_type or not bank or not investors or not share_equivalent:
                filings_to_process.append(filing)
        
        print(f"[Backfill] ✓ Found {len(filings_to_process)} filings that need backfilling")
        print(f"[Backfill]   (out of {len(all_filings)} total filings)\n")
        
        if not filings_to_process:
            print("[Backfill] ✅ All filings already have the new fields populated")
            return 0
        
        # Process each filing
        print("[Backfill] Step 2: Re-parsing filings...")
        print("-" * 80)
        
        updated_count = 0
        error_count = 0
        
        for i, filing in enumerate(filings_to_process, 1):
            ticker = filing.get('ticker', 'UNKNOWN')
            form_type = filing.get('form_type', 'UNKNOWN')
            date = filing.get('date', 'N/A')
            link = filing.get('link_to_filing', '')
            filing_id = filing.get('id')
            
            print(f"[Backfill] [{i}/{len(filings_to_process)}] Processing {ticker} ({form_type}) - {date}...")
            
            if not link:
                print(f"  ⚠️  Skipping: No link_to_filing")
                error_count += 1
                continue
            
            # Parse filing details (parse_filing_details will fetch the HTML)
            try:
                # Create a minimal filing dict for parsing
                filing_dict = {
                    'link': link,
                    'form_type': form_type,
                    'ticker': ticker,
                    'pubDate': date,
                }
                
                # Parse the filing (this will fetch and parse the HTML)
                parsed_details = parse_filing_details(filing_dict, max_price=None)
                
                # Extract the new fields
                offering_type = parsed_details.get('offering_type')
                bank = parsed_details.get('bank')  # First underwriter
                investors = parsed_details.get('investors')
                share_equivalent = parsed_details.get('share_equivalent')
                
                # Build update dict (only include fields that were extracted)
                updates = {}
                if offering_type:
                    updates['offering_type'] = offering_type
                if bank:
                    updates['bank'] = bank
                if investors:
                    updates['investors'] = investors
                if share_equivalent:
                    updates['share_equivalent'] = share_equivalent
                
                if not updates:
                    print(f"  ⚠️  No new fields extracted")
                    continue
                
                # Show what will be updated
                print(f"  ✓ Extracted:")
                for key, value in updates.items():
                    display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    print(f"    - {key}: {display_value}")
                
                # Update database if not dry run
                if not dry_run:
                    try:
                        client.table(table_name).update(updates).eq('id', filing_id).execute()
                        updated_count += 1
                        print(f"  ✅ Updated database record")
                    except Exception as e:
                        print(f"  ❌ Error updating database: {e}")
                        error_count += 1
                else:
                    updated_count += 1  # Count for dry run
                    print(f"  [DRY RUN] Would update database record")
                
                # Rate limiting: delay between requests
                time.sleep(SEC_REQUEST_DELAY)
                
            except Exception as e:
                print(f"  ❌ Error parsing filing: {e}")
                import traceback
                traceback.print_exc()
                error_count += 1
                continue
        
        print()
        print("=" * 80)
        print("BACKFILL SUMMARY")
        print("=" * 80)
        print(f"Filings processed: {len(filings_to_process)}")
        print(f"Successfully updated: {updated_count}")
        print(f"Errors: {error_count}")
        if dry_run:
            print(f"\n⚠️  This was a DRY RUN. Run without --dry-run to apply changes.")
        
        return updated_count
        
    except Exception as e:
        print(f"[Backfill] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill new fields (offering_type, bank, investors, share_equivalent) for existing filings")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of filings to process (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be updated without making changes")
    
    args = parser.parse_args()
    
    # Initialize Supabase
    client = init_supabase()
    if not client:
        print("❌ Failed to initialize Supabase client")
        print("   Make sure SUPABASE_URL and SUPABASE_ANON_KEY are set")
        sys.exit(1)
    
    # Run backfill
    updated = backfill_new_fields(
        client,
        limit=args.limit,
        dry_run=args.dry_run
    )
    
    if updated > 0:
        print(f"\n✅ Backfill complete: {updated} filings updated")
    else:
        print(f"\n⚠️  No filings were updated")
    
    sys.exit(0 if updated > 0 or args.dry_run else 1)
