"""
Import CSV to Supabase: Uploads CSV data to Supabase database

This script reads the dilution_alerts.csv file and imports all records
into Supabase, handling deduplication automatically.
"""

import os
import sys
import pandas as pd
from datetime import datetime
from typing import Optional
from supabase_storage import init_supabase, save_alerts_to_db

def parse_currency(value) -> Optional[float]:
    """
    Parse currency strings like "$10,000,000" or "$0.50 per share" to float.
    Returns None if parsing fails.
    """
    if pd.isna(value) or value == "":
        return None
    
    value_str = str(value).strip()
    if not value_str or value_str == "N/A":
        return None
    
    # Remove currency symbols and "per share" text
    value_str = value_str.replace("$", "").replace(",", "").strip()
    
    # Remove "per share" or similar text
    if "per share" in value_str.lower():
        value_str = value_str.lower().split("per share")[0].strip()
    if "per share" in value_str:
        value_str = value_str.split("per share")[0].strip()
    
    try:
        return float(value_str)
    except (ValueError, TypeError):
        return None


def csv_row_to_filing_dict(row: pd.Series) -> dict:
    """
    Convert a CSV row to a filing dictionary format expected by save_alerts_to_db.
    """
    # Parse risk_score as integer (database expects integer)
    risk_score_raw = row.get("Risk_Score", 0)
    if pd.notna(risk_score_raw):
        try:
            risk_score = int(float(risk_score_raw))  # Convert to int via float first
        except (ValueError, TypeError):
            risk_score = 0
    else:
        risk_score = 0
    
    filing = {
        "ticker": str(row.get("Ticker", "")).upper().strip(),
        "form_type": str(row.get("Form_Type", "")).strip(),
        "date": str(row.get("Date", "")).strip(),
        "link": str(row.get("Link_to_Filing", "")).strip(),
        "title": str(row.get("Title", "")).strip() if pd.notna(row.get("Title")) else "",
        "pubDate": str(row.get("Date", "")).strip(),  # Use Date as pubDate
        "risk_score": risk_score,  # Integer, not float
        "has_red_flags": str(row.get("Red_Flags_Found", "")).strip() != "" if pd.notna(row.get("Red_Flags_Found")) else False,
        "red_flags_found": set(str(row.get("Red_Flags_Found", "")).split(",")) if pd.notna(row.get("Red_Flags_Found")) and str(row.get("Red_Flags_Found", "")).strip() != "" else set(),
        "warrants_found": str(row.get("Warrants_Found", "")).strip().lower() in ["yes", "true", "1"] if pd.notna(row.get("Warrants_Found")) else False,
        "underwriters": [u.strip() for u in str(row.get("Underwriter_Found", "")).split(",") if u.strip()] if pd.notna(row.get("Underwriter_Found")) and str(row.get("Underwriter_Found", "")).strip() != "" else [],
        "base_offering_amount": parse_currency(row.get("Offering_Amount")) or parse_currency(row.get("Base_Offering_Amount")),
        "share_price": parse_currency(row.get("Share_Price")),
        "cik": str(row.get("CIK", "")).strip() if pd.notna(row.get("CIK")) else None,
    }
    
    # Parse additional fields if they exist
    if pd.notna(row.get("Number_of_Shares")):
        try:
            shares_str = str(row.get("Number_of_Shares", "")).replace(",", "").strip()
            filing["number_of_shares"] = int(float(shares_str)) if shares_str else None
        except (ValueError, TypeError):
            filing["number_of_shares"] = None
    
    # Convert red_flags_found set to list for JSON serialization
    filing["red_flags_found"] = list(filing["red_flags_found"])
    
    return filing


def import_csv_to_supabase(csv_path: str = "data/dilution_alerts.csv", batch_size: int = 100):
    """
    Import CSV file to Supabase database.
    
    Args:
        csv_path: Path to CSV file
        batch_size: Number of records to process in each batch
    """
    print("=" * 80)
    print("IMPORT CSV TO SUPABASE")
    print("=" * 80)
    print(f"CSV file: {csv_path}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check if CSV exists
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        sys.exit(1)
    
    # Initialize Supabase
    print("[Import] Step 1: Initializing Supabase connection...")
    client = init_supabase()
    if not client:
        print("❌ Supabase not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")
        print("\nTo set environment variables:")
        print("  export SUPABASE_URL='https://your-project.supabase.co'")
        print("  export SUPABASE_ANON_KEY='your-anon-key'")
        print("\nOr create a .env file in the project root with:")
        print("  SUPABASE_URL=https://your-project.supabase.co")
        print("  SUPABASE_ANON_KEY=your-anon-key")
        sys.exit(1)
    print("[Import] ✓ Supabase connected\n")
    
    # Read CSV
    print("[Import] Step 2: Reading CSV file...")
    try:
        df = pd.read_csv(csv_path)
        print(f"[Import] ✓ Loaded {len(df)} records from CSV\n")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        sys.exit(1)
    
    # Convert CSV rows to filing dictionaries
    print("[Import] Step 3: Converting CSV rows to filing format...")
    filings = []
    skipped = 0
    
    for idx, row in df.iterrows():
        try:
            filing = csv_row_to_filing_dict(row)
            
            # Skip UNKNOWN tickers
            if not filing.get("ticker") or filing.get("ticker") == "UNKNOWN":
                skipped += 1
                continue
            
            # Skip if missing required fields
            if not filing.get("date") or not filing.get("form_type"):
                skipped += 1
                continue
            
            filings.append(filing)
        except Exception as e:
            print(f"  ⚠️  Error processing row {idx + 1}: {e}")
            skipped += 1
    
    print(f"[Import] ✓ Converted {len(filings)} filings (skipped {skipped} invalid rows)\n")
    
    if not filings:
        print("⚠️  No valid filings to import")
        sys.exit(0)
    
    # Save to Supabase in batches
    print("[Import] Step 4: Uploading to Supabase (with automatic deduplication)...")
    print(f"[Import] Processing {len(filings)} filings in batches of {batch_size}...")
    
    total_saved = 0
    for i in range(0, len(filings), batch_size):
        batch = filings[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(filings) + batch_size - 1) // batch_size
        
        print(f"[Import] Batch {batch_num}/{total_batches} ({len(batch)} filings)...")
        
        try:
            success = save_alerts_to_db(batch, client)
            if success:
                total_saved += len(batch)
                print(f"  ✓ Saved batch {batch_num} ({len(batch)} filings)")
            else:
                print(f"  ⚠️  Batch {batch_num} save returned False (may have duplicates)")
        except Exception as e:
            print(f"  ❌ Error saving batch {batch_num}: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 80)
    print("IMPORT SUMMARY")
    print("=" * 80)
    print(f"Total records in CSV: {len(df)}")
    print(f"Valid filings converted: {len(filings)}")
    print(f"Skipped (invalid): {skipped}")
    print(f"Batches processed: {total_batches}")
    print(f"Total saved to Supabase: {total_saved}")
    print()
    print("Note: Supabase automatically handles deduplication based on")
    print("      (ticker, date, form_type) combination.")
    print()
    print("✅ Import complete!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Import CSV file to Supabase")
    parser.add_argument("--csv", type=str, default="data/dilution_alerts.csv", help="Path to CSV file")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for uploads (default: 100)")
    
    args = parser.parse_args()
    
    import_csv_to_supabase(csv_path=args.csv, batch_size=args.batch_size)
