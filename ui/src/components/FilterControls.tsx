import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Star } from "lucide-react"

export interface Filters {
  // Server-side (trigger re-fetch)
  zipCode: string
  estimatedUse: number
  planType: string // "" = all, "1" = fixed, "0" = variable

  // Client-side
  priceMin: number
  priceMax: number
  termMin: number
  termMax: number
  prepaid: "all" | "only" | "hide"
  timeOfUse: "all" | "only" | "hide"
  minRating: number // 0 = no filter, 1-5 = minimum stars
  renewableRange: string // "all" | "100" | "76-99" | "51-75" | "26-50" | "0-25"
  company: string // "" = all, or company name
  hideMinUsage: boolean
}

const USAGE_OPTIONS = [500, 1000, 2000]

const RENEWABLE_OPTIONS = [
  { value: "all", label: "All" },
  { value: "100", label: "100% Renewable" },
  { value: "76-99", label: "76% to 99%" },
  { value: "51-75", label: "51% to 75%" },
  { value: "26-50", label: "26% to 50%" },
  { value: "0-25", label: "0% to 25%" },
]

interface FilterControlsProps {
  filters: Filters
  onChange: (filters: Filters) => void
  onSearch: () => void
  loading: boolean
  planCount: number
  totalCount: number
  companies: string[]
}

function StarRating({
  value,
  onChange,
}: {
  value: number
  onChange: (v: number) => void
}) {
  return (
    <div className="flex gap-1 items-center">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          onClick={() => onChange(value === star ? 0 : star)}
          className="p-0.5 hover:scale-110 transition-transform"
          title={value === star ? "Clear rating filter" : `${star}+ stars`}
        >
          <Star
            className={`h-5 w-5 ${
              star <= value
                ? "fill-yellow-400 text-yellow-400"
                : "text-muted-foreground/30"
            }`}
          />
        </button>
      ))}
      {value > 0 && (
        <span className="text-xs text-muted-foreground ml-1">{value}+ stars</span>
      )}
    </div>
  )
}

function TriToggle({
  value,
  onChange,
  labels,
}: {
  value: "all" | "only" | "hide"
  onChange: (v: "all" | "only" | "hide") => void
  labels: { all: string; only: string; hide: string }
}) {
  return (
    <div className="flex gap-1">
      {(["all", "only", "hide"] as const).map((opt) => (
        <Button
          key={opt}
          variant={value === opt ? "default" : "outline"}
          size="sm"
          className="text-xs h-7 px-2"
          onClick={() => onChange(opt)}
        >
          {labels[opt]}
        </Button>
      ))}
    </div>
  )
}

export function FilterControls({
  filters,
  onChange,
  onSearch,
  loading,
  planCount,
  totalCount,
  companies,
}: FilterControlsProps) {
  const [zipInput, setZipInput] = useState(filters.zipCode)

  function handleSearch() {
    onChange({ ...filters, zipCode: zipInput })
    onSearch()
  }

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Filters</CardTitle>
          <div className="text-sm text-muted-foreground">
            {planCount} of {totalCount} plans
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Row 1: Search controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Zip Code */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Zip Code</Label>
            <div className="flex gap-2">
              <Input
                value={zipInput}
                onChange={(e) => setZipInput(e.target.value)}
                placeholder="e.g. 78665"
                maxLength={5}
                className="h-8"
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              />
              <Button
                onClick={handleSearch}
                disabled={loading || zipInput.length !== 5}
                size="sm"
                className="h-8"
              >
                {loading ? "..." : "Go"}
              </Button>
            </div>
          </div>

          {/* Estimated Usage */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Estimated Usage</Label>
            <div className="flex gap-1">
              {USAGE_OPTIONS.map((use) => (
                <Button
                  key={use}
                  variant={filters.estimatedUse === use ? "default" : "outline"}
                  size="sm"
                  className="h-8 text-xs"
                  onClick={() => onChange({ ...filters, estimatedUse: use })}
                >
                  {use} kWh
                </Button>
              ))}
            </div>
          </div>

          {/* Plan Type */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Plan Type</Label>
            <div className="flex gap-1">
              {[
                { value: "", label: "All" },
                { value: "1", label: "Fixed" },
                { value: "0", label: "Variable" },
              ].map((opt) => (
                <Button
                  key={opt.value}
                  variant={filters.planType === opt.value ? "default" : "outline"}
                  size="sm"
                  className="h-8 text-xs"
                  onClick={() => onChange({ ...filters, planType: opt.value })}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Company */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Electric Company</Label>
            <Select
              value={filters.company}
              onValueChange={(v) => onChange({ ...filters, company: v === "all" ? "" : v })}
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue placeholder="All companies" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Companies</SelectItem>
                {companies.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <Separator />

        {/* Row 2: Range filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Price Range */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Price/kWh (¢)</Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                value={filters.priceMin || ""}
                onChange={(e) =>
                  onChange({ ...filters, priceMin: Number(e.target.value) || 0 })
                }
                placeholder="Min"
                className="h-8 text-xs w-20"
                step={0.5}
              />
              <span className="text-xs text-muted-foreground">to</span>
              <Input
                type="number"
                value={filters.priceMax || ""}
                onChange={(e) =>
                  onChange({ ...filters, priceMax: Number(e.target.value) || 99 })
                }
                placeholder="Max"
                className="h-8 text-xs w-20"
                step={0.5}
              />
            </div>
          </div>

          {/* Contract Length */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Contract Length (months)</Label>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                value={filters.termMin || ""}
                onChange={(e) =>
                  onChange({ ...filters, termMin: Number(e.target.value) || 0 })
                }
                placeholder="Min"
                className="h-8 text-xs w-20"
                min={0}
              />
              <span className="text-xs text-muted-foreground">to</span>
              <Input
                type="number"
                value={filters.termMax || ""}
                onChange={(e) =>
                  onChange({ ...filters, termMax: Number(e.target.value) || 99 })
                }
                placeholder="Max"
                className="h-8 text-xs w-20"
                min={0}
              />
            </div>
          </div>

          {/* Renewable Energy */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Renewable Energy</Label>
            <Select
              value={filters.renewableRange}
              onValueChange={(v) => onChange({ ...filters, renewableRange: v })}
            >
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RENEWABLE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Company Rating */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Minimum Company Rating</Label>
            <StarRating
              value={filters.minRating}
              onChange={(v) => onChange({ ...filters, minRating: v })}
            />
          </div>
        </div>

        <Separator />

        {/* Row 3: Toggle filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Prepaid */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Prepaid Plans</Label>
            <TriToggle
              value={filters.prepaid}
              onChange={(v) => onChange({ ...filters, prepaid: v })}
              labels={{ all: "Show All", only: "Only Prepaid", hide: "Hide" }}
            />
          </div>

          {/* Time of Use */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Time of Use Plans</Label>
            <TriToggle
              value={filters.timeOfUse}
              onChange={(v) => onChange({ ...filters, timeOfUse: v })}
              labels={{ all: "Show All", only: "Only TOU", hide: "Hide" }}
            />
          </div>

          {/* Min Usage / Tiered Pricing */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Pricing & Billing</Label>
            <div className="flex gap-1">
              <Button
                variant={filters.hideMinUsage ? "default" : "outline"}
                size="sm"
                className="h-7 text-xs"
                onClick={() => onChange({ ...filters, hideMinUsage: !filters.hideMinUsage })}
              >
                {filters.hideMinUsage ? "Hiding min usage plans" : "Showing all"}
              </Button>
            </div>
          </div>

          {/* Quick term badges */}
          <div className="space-y-1.5">
            <Label className="text-xs font-medium">Quick Term Select</Label>
            <div className="flex flex-wrap gap-1">
              {[6, 12, 24, 36].map((term) => (
                <Badge
                  key={term}
                  variant={
                    filters.termMin <= term && filters.termMax >= term
                      ? "default"
                      : "outline"
                  }
                  className="cursor-pointer select-none text-xs"
                  onClick={() =>
                    onChange({ ...filters, termMin: term, termMax: term })
                  }
                >
                  {term}mo
                </Badge>
              ))}
              <Badge
                variant="outline"
                className="cursor-pointer select-none text-xs"
                onClick={() => onChange({ ...filters, termMin: 0, termMax: 99 })}
              >
                Any
              </Badge>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
