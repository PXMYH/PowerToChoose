import type { Plan } from "@/types/plan"

export async function fetchPlans(
  zipCode: string,
  estimatedUse: number
): Promise<Plan[]> {
  const params = new URLSearchParams({
    zip_code: zipCode,
    estimated_use: String(estimatedUse),
  })
  const res = await fetch(`/api/plans?${params}`)
  if (!res.ok) throw new Error(`Failed to fetch plans: ${res.statusText}`)
  return res.json()
}
