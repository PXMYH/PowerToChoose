import type { Plan } from "@/types/plan"

export interface FetchPlansParams {
  zipCode: string
  estimatedUse: number
  planType: string // "" = all, "1" = fixed, "0" = variable
}

export async function fetchPlans(params: FetchPlansParams): Promise<Plan[]> {
  const searchParams = new URLSearchParams({
    zip_code: params.zipCode,
    estimated_use: String(params.estimatedUse),
    plan_type: params.planType,
  })
  const res = await fetch(`/api/plans?${searchParams}`)
  if (!res.ok) throw new Error(`Failed to fetch plans: ${res.statusText}`)
  return res.json()
}
