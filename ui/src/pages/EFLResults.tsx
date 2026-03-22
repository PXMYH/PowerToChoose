import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

interface PricingTier {
  usage_kwh: number
  price_per_kwh: number
}

interface Charge {
  charge_type: string
  amount: number
  unit: string
  threshold_kwh: number | null
}

interface EFLPlan {
  id: number
  plan_id: string
  provider_name: string
  plan_name: string
  plan_type: string
  contract_term_months: number | null
  early_termination_fee: number | null
  etf_conditions: string | null
  renewable_energy_pct: number | null
  special_terms: string | null
  efl_url: string | null
  extracted_at: string
  pricing_tiers: PricingTier[]
  charges: Charge[]
}

interface ValidationIssue {
  field: string
  issue: string
  severity: string
}

interface ValidationResult {
  plan_id: string
  confidence_score: number
  issues: ValidationIssue[]
}

const chargeTypeLabels: Record<string, string> = {
  base: "Base Charge",
  energy: "Energy Charge",
  tdu_delivery: "TDU Delivery",
  tdu_fixed: "TDU Fixed",
  minimum_usage: "Minimum Usage",
}

function confidenceColor(score: number): string {
  if (score >= 0.8) return "text-green-600 dark:text-green-400"
  if (score >= 0.5) return "text-yellow-600 dark:text-yellow-400"
  return "text-red-600 dark:text-red-400"
}

function confidenceBadge(score: number) {
  if (score >= 0.8) return "default" as const
  if (score >= 0.5) return "secondary" as const
  return "destructive" as const
}

export default function EFLResults() {
  const [plans, setPlans] = useState<EFLPlan[]>([])
  const [validations, setValidations] = useState<Record<string, ValidationResult>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedPlan, setExpandedPlan] = useState<number | null>(null)

  const base = import.meta.env.VITE_API_URL || ""

  useEffect(() => {
    async function loadPlans() {
      try {
        const res = await fetch(`${base}/api/efl/plans`)
        if (!res.ok) throw new Error(`Failed to fetch EFL plans: ${res.statusText}`)
        const data = await res.json()
        setPlans(data.plans)

        // Fetch validation for each plan in parallel
        const validationResults: Record<string, ValidationResult> = {}
        await Promise.allSettled(
          data.plans.map(async (plan: EFLPlan) => {
            try {
              const vRes = await fetch(`${base}/api/efl/validate/${plan.plan_id}`)
              if (vRes.ok) {
                validationResults[plan.plan_id] = await vRes.json()
              }
            } catch {
              // Validation is optional — skip on failure
            }
          })
        )
        setValidations(validationResults)
      } catch (e) {
        setError(e instanceof Error ? e.message : "Unknown error")
      } finally {
        setLoading(false)
      }
    }
    loadPlans()
  }, [base])

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold tracking-tight">EFL Results</h1>
          <p className="text-sm text-muted-foreground">
            Extracted plan data from Electricity Facts Labels
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 space-y-4">
        {loading && (
          <p className="text-center py-12 text-muted-foreground">Loading extracted plans...</p>
        )}
        {error && <p className="text-center py-12 text-red-500">{error}</p>}
        {!loading && !error && plans.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              No extracted EFL data yet. Process some plans first via the API.
            </CardContent>
          </Card>
        )}

        {!loading && !error && plans.length > 0 && (
          <>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>{plans.length} plan{plans.length !== 1 ? "s" : ""} extracted</span>
            </div>

            <div className="space-y-3">
              {plans.map((plan) => {
                const validation = validations[plan.plan_id]
                const isExpanded = expandedPlan === plan.id

                return (
                  <Card
                    key={plan.id}
                    className={cn(
                      "cursor-pointer transition-shadow hover:shadow-md",
                      isExpanded && "ring-1 ring-primary"
                    )}
                    onClick={() => setExpandedPlan(isExpanded ? null : plan.id)}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <CardTitle className="text-base truncate">
                            {plan.plan_name}
                          </CardTitle>
                          <p className="text-sm text-muted-foreground mt-0.5">
                            {plan.provider_name}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <Badge variant={plan.plan_type === "fixed" ? "default" : "secondary"}>
                            {plan.plan_type}
                          </Badge>
                          {validation && (
                            <Badge variant={confidenceBadge(validation.confidence_score)}>
                              <span className={confidenceColor(validation.confidence_score)}>
                                {(validation.confidence_score * 100).toFixed(0)}%
                              </span>
                            </Badge>
                          )}
                        </div>
                      </div>

                      {/* Summary row */}
                      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-muted-foreground">
                        {plan.contract_term_months != null && (
                          <span>{plan.contract_term_months} mo term</span>
                        )}
                        {plan.renewable_energy_pct != null && (
                          <span>{plan.renewable_energy_pct}% renewable</span>
                        )}
                        {plan.early_termination_fee != null && plan.early_termination_fee > 0 && (
                          <span>ETF: ${plan.early_termination_fee}</span>
                        )}
                        <span>Extracted: {new Date(plan.extracted_at).toLocaleDateString()}</span>
                      </div>
                    </CardHeader>

                    {isExpanded && (
                      <CardContent className="pt-0" onClick={(e) => e.stopPropagation()}>
                        <Separator className="mb-4" />

                        {/* Pricing Tiers */}
                        {plan.pricing_tiers.length > 0 && (
                          <div className="mb-4">
                            <h4 className="text-sm font-medium mb-2">Pricing Tiers</h4>
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Usage (kWh)</TableHead>
                                  <TableHead className="text-right">Price per kWh</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {plan.pricing_tiers.map((tier) => (
                                  <TableRow key={tier.usage_kwh}>
                                    <TableCell>{tier.usage_kwh.toLocaleString()}</TableCell>
                                    <TableCell className="text-right">
                                      {tier.price_per_kwh > 0
                                        ? `${tier.price_per_kwh.toFixed(1)}\u00A2`
                                        : "N/A"}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        )}

                        {/* Charges */}
                        {plan.charges.length > 0 && (
                          <div className="mb-4">
                            <h4 className="text-sm font-medium mb-2">Charges</h4>
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead>Type</TableHead>
                                  <TableHead className="text-right">Amount</TableHead>
                                  <TableHead>Unit</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {plan.charges.map((charge, i) => (
                                  <TableRow key={i}>
                                    <TableCell>
                                      {chargeTypeLabels[charge.charge_type] || charge.charge_type}
                                    </TableCell>
                                    <TableCell className="text-right">
                                      ${charge.amount.toFixed(4)}
                                    </TableCell>
                                    <TableCell>
                                      {charge.unit === "monthly" ? "/mo" : "/kWh"}
                                      {charge.threshold_kwh != null && (
                                        <span className="text-muted-foreground">
                                          {" "}(min {charge.threshold_kwh} kWh)
                                        </span>
                                      )}
                                    </TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        )}

                        {/* Validation Issues */}
                        {validation && validation.issues.length > 0 && (
                          <div className="mb-4">
                            <h4 className="text-sm font-medium mb-2">Validation Issues</h4>
                            <div className="space-y-1">
                              {validation.issues.map((issue, i) => (
                                <div
                                  key={i}
                                  className={cn(
                                    "text-xs px-2 py-1 rounded",
                                    issue.severity === "error"
                                      ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
                                      : "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
                                  )}
                                >
                                  <span className="font-medium">{issue.field}:</span> {issue.issue}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Special Terms */}
                        {plan.special_terms && (
                          <div className="mb-4">
                            <h4 className="text-sm font-medium mb-1">Special Terms</h4>
                            <p className="text-xs text-muted-foreground">{plan.special_terms}</p>
                          </div>
                        )}

                        {/* EFL Link */}
                        {plan.efl_url && (
                          <a
                            href={plan.efl_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary underline"
                          >
                            View original EFL PDF
                          </a>
                        )}
                      </CardContent>
                    )}
                  </Card>
                )
              })}
            </div>
          </>
        )}
      </main>
    </div>
  )
}
