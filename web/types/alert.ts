export interface DilutionAlert {
  id: number;
  date: string;
  filing_datetime?: string | null; // ISO datetime string (includes time)
  ticker: string;
  company_name?: string | null; // Company name from company_universe table
  country?: string | null; // Company country from company_universe table
  form_type: string;
  link_to_filing: string | null;
  warrants_found: boolean;
  underwriter_found: string | null;
  red_flags_found: string | null;
  risk_score: number;
  cap_raise_amount: number | null;
  toxic_debt_detected: boolean;
  toxic_debt_snippet: string | null;
  management_turnover: boolean;
  resignation_snippet: string | null;
  warrant_coverage: string | null;
  base_offering_amount: string | null;
  offering_amount: string | null;
  share_price: string | null;
  number_of_shares: string | null;
  overallotment_shares: string | null;
  overallotment_amount: string | null;
  has_warrants: boolean | null;
  warrants_per_share: string | null;
  private_placement_shares: string | null;
  private_placement_amount: string | null;
  additional_dilutions: string | null;
  price_at_filing: number | null;
  price_7days_later: number | null;
  offering_type: string | null;
  bank: string | null;
  investors: string | null;
  share_equivalent: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlertFilters {
  ticker?: string;
  formType?: string;
  minRiskScore?: number;
  daysBack?: number;
  limit?: number;
  watchlistOnly?: boolean;
  country?: string;
}
