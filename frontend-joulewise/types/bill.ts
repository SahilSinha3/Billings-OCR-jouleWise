export interface MeterReading {
  id?: string;
  meter_number: string;
  reading_type: string;
  previous_reading: number;
  current_reading: number;
  difference: number;
  multiplying_factor: number;
  consumed_units: number;
}

export interface BillLineItem {
  id?: string;
  category: string;
  description: string;
  rate?: number | null;
  quantity?: number | null;
  amount: number;
}

export interface DiscrepancyItem {
  rule_name: string;
  field_name: string;
  expected_value: number;
  reported_value: number;
  discrepancy_delta: number;
  severity: "CRITICAL" | "WARNING" | "INFO";
}

export interface MathVerificationReport {
  is_valid: boolean;
  units_verified: boolean;
  financial_verified: boolean;
  power_factor_valid: boolean;
  dates_valid: boolean;
  discrepancies: DiscrepancyItem[];
}

export interface BillDetail {
  id: string;
  discom_code: string;
  discom_name: string;
  consumer_number: string;
  account_number?: string | null;
  consumer_name: string;
  billing_address?: string | null;
  bill_number: string;
  bill_date?: string | null;
  billing_period_start?: string | null;
  billing_period_end?: string | null;
  due_date?: string | null;
  tariff_category?: string | null;
  sanctioned_load_kw?: number | null;
  contract_demand_kva?: number | null;
  billed_demand_kva?: number | null;
  power_factor?: number | null;
  total_units_kwh: number;
  total_units_kvah?: number | null;
  total_current_charges: number;
  net_amount_due: number;
  amount_after_due_date?: number | null;
  status: "QUEUED" | "EXTRACTING" | "VERIFIED" | "FLAGGED_FOR_REVIEW" | "FAILED" | "REJECTED_NON_BILL";
  is_valid_bill?: boolean;
  validation_error?: string | null;
  bill_summary?: string | null;
  raw_extracted_text?: string | null;
  confidence_score: number;
  is_math_verified: boolean;
  verification_details?: MathVerificationReport | null;
  readings: MeterReading[];
  line_items: BillLineItem[];
  created_at: string;
  updated_at: string;
}
