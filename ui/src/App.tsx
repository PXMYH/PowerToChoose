import { useCallback, useEffect, useMemo, useState } from "react"
import { PlanTable } from "@/components/PlanTable"
import { FilterControls, type Filters } from "@/components/FilterControls"
import { fetchPlans } from "@/lib/api"
import type { Plan } from "@/types/plan"

const DEFAULT_FILTERS: Filters = {
  zipCode: "78665",
  estimatedUse: 1000,
  planType: "",
  priceMin: 0,
  priceMax: 99,
  termMin: 0,
  termMax: 99,
  prepaid: "hide",
  timeOfUse: "all",
  minRating: 0,
  renewableRange: "all",
  company: "",
  hideMinUsage: false,
}

function getRenewablePct(desc: string): number {
  const match = desc.match(/(\d+)%/)
  return match ? parseInt(match[1]) : 0
}

function matchesRenewableRange(desc: string, range: string): boolean {
  if (range === "all") return true
  const pct = getRenewablePct(desc)
  switch (range) {
    case "100": return pct === 100
    case "76-99": return pct >= 76 && pct <= 99
    case "51-75": return pct >= 51 && pct <= 75
    case "26-50": return pct >= 26 && pct <= 50
    case "0-25": return pct >= 0 && pct <= 25
    default: return true
  }
}

function App() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)

  const loadPlans = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchPlans({
        zipCode: filters.zipCode,
        estimatedUse: filters.estimatedUse,
        planType: filters.planType,
      })
      setPlans(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [filters.zipCode, filters.estimatedUse, filters.planType])

  useEffect(() => {
    loadPlans()
  }, [loadPlans])

  // Unique sorted company names from current data
  const companies = useMemo(
    () => [...new Set(plans.map((p) => p.company_name))].sort(),
    [plans]
  )

  const filteredPlans = useMemo(() => {
    return plans.filter((p) => {
      const price = p.price_kwh1000
      if (filters.priceMin > 0 && price < filters.priceMin) return false
      if (filters.priceMax < 99 && price > filters.priceMax) return false

      if (filters.termMin > 0 && p.term_value < filters.termMin) return false
      if (filters.termMax < 99 && p.term_value > filters.termMax) return false

      if (filters.prepaid === "hide" && p.prepaid) return false
      if (filters.prepaid === "only" && !p.prepaid) return false

      if (filters.timeOfUse === "hide" && p.timeofuse) return false
      if (filters.timeOfUse === "only" && !p.timeofuse) return false

      if (filters.minRating > 0 && p.rating_total < filters.minRating) return false

      if (!matchesRenewableRange(p.renewable_energy_description, filters.renewableRange))
        return false

      if (filters.company && p.company_name !== filters.company) return false

      if (filters.hideMinUsage && p.minimum_usage) return false

      return true
    })
  }, [plans, filters])

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold tracking-tight">Power to Choose</h1>
          <p className="text-sm text-muted-foreground">
            Compare Texas electricity plans
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <FilterControls
          filters={filters}
          onChange={setFilters}
          onSearch={loadPlans}
          loading={loading}
          planCount={filteredPlans.length}
          totalCount={plans.length}
          companies={companies}
        />

        {loading && (
          <p className="text-center py-12 text-muted-foreground">Loading plans...</p>
        )}
        {error && <p className="text-center py-12 text-red-500">{error}</p>}
        {!loading && !error && <PlanTable data={filteredPlans} />}
      </main>
    </div>
  )
}

export default App
