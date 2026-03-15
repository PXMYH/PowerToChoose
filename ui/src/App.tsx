import { useCallback, useEffect, useMemo, useState } from "react"
import { PlanTable } from "@/components/PlanTable"
import { FilterControls, type Filters } from "@/components/FilterControls"
import { fetchPlans } from "@/lib/api"
import type { Plan } from "@/types/plan"

const DEFAULT_FILTERS: Filters = {
  zipCode: "78665",
  estimatedUse: 1000,
  maxPrice: 20,
  termLengths: [],
  renewableOnly: false,
  hidePrepaid: true,
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
      const data = await fetchPlans(filters.zipCode, filters.estimatedUse)
      setPlans(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [filters.zipCode, filters.estimatedUse])

  useEffect(() => {
    loadPlans()
  }, [loadPlans])

  const filteredPlans = useMemo(() => {
    return plans.filter((p) => {
      if (p.price_kwh1000 > filters.maxPrice) return false
      if (filters.termLengths.length > 0 && !filters.termLengths.includes(p.term_value))
        return false
      if (filters.renewableOnly && p.renewable_energy_description !== "100% Renewable")
        return false
      if (filters.hidePrepaid && p.prepaid) return false
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
