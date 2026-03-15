import { useEffect, useState } from "react"
import { PlanTable } from "@/components/PlanTable"
import { fetchPlans } from "@/lib/api"
import type { Plan } from "@/types/plan"

function App() {
  const [plans, setPlans] = useState<Plan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchPlans("78665", 1000)
      .then(setPlans)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

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
        {loading && <p className="text-center py-12 text-muted-foreground">Loading plans...</p>}
        {error && <p className="text-center py-12 text-red-500">{error}</p>}
        {!loading && !error && <PlanTable data={plans} />}
      </main>
    </div>
  )
}

export default App
