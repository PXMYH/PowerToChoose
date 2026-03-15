export interface Plan {
  plan_id: number
  zip_code: string
  company_name: string
  company_logo: string
  website: string
  plan_name: string
  plan_type: number
  special_terms: string
  rate_type: string
  term_value: number
  price_kwh500: number
  price_kwh1000: number
  price_kwh2000: number
  prepaid: boolean
  timeofuse: boolean
  pricing_details: string
  fact_sheet: string
  terms_of_service: string
  go_to_plan: string
  enroll_phone: string
  renewable_energy_id: number
  renewable_energy_description: string
  rating_total: number
  rating_count: number
  new_customer: boolean
  minimum_usage: boolean
}
