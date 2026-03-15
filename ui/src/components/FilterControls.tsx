import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Slider } from "@/components/ui/slider"
import { Card, CardContent } from "@/components/ui/card"

export interface Filters {
  zipCode: string
  estimatedUse: number
  maxPrice: number
  termLengths: number[]
  renewableOnly: boolean
  hidePrepaid: boolean
}

const TERM_OPTIONS = [3, 6, 12, 18, 24, 36, 48, 60]
const USAGE_OPTIONS = [500, 1000, 2000]

interface FilterControlsProps {
  filters: Filters
  onChange: (filters: Filters) => void
  onSearch: () => void
  loading: boolean
  planCount: number
}

export function FilterControls({
  filters,
  onChange,
  onSearch,
  loading,
  planCount,
}: FilterControlsProps) {
  const [zipInput, setZipInput] = useState(filters.zipCode)

  function toggleTerm(term: number) {
    const next = filters.termLengths.includes(term)
      ? filters.termLengths.filter((t) => t !== term)
      : [...filters.termLengths, term]
    onChange({ ...filters, termLengths: next })
  }

  function handleSearch() {
    onChange({ ...filters, zipCode: zipInput })
    onSearch()
  }

  return (
    <Card className="mb-6">
      <CardContent className="pt-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Zip Code + Search */}
          <div className="space-y-2">
            <Label>Zip Code</Label>
            <div className="flex gap-2">
              <Input
                value={zipInput}
                onChange={(e) => setZipInput(e.target.value)}
                placeholder="e.g. 78665"
                maxLength={5}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              />
              <Button onClick={handleSearch} disabled={loading || zipInput.length !== 5}>
                {loading ? "..." : "Search"}
              </Button>
            </div>
          </div>

          {/* Estimated Usage */}
          <div className="space-y-2">
            <Label>Estimated Usage</Label>
            <div className="flex gap-1">
              {USAGE_OPTIONS.map((use) => (
                <Button
                  key={use}
                  variant={filters.estimatedUse === use ? "default" : "outline"}
                  size="sm"
                  onClick={() => {
                    onChange({ ...filters, estimatedUse: use })
                  }}
                >
                  {use} kWh
                </Button>
              ))}
            </div>
          </div>

          {/* Max Price */}
          <div className="space-y-2">
            <Label>Max Price: {filters.maxPrice}¢/kWh</Label>
            <Slider
              value={[filters.maxPrice]}
              onValueChange={(v) => onChange({ ...filters, maxPrice: Array.isArray(v) ? v[0] : v })}
              min={5}
              max={20}
              step={0.5}
            />
          </div>

          {/* Toggles */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Switch
                checked={filters.renewableOnly}
                onCheckedChange={(v) => onChange({ ...filters, renewableOnly: v })}
              />
              <Label>100% Renewable only</Label>
            </div>
            <div className="flex items-center gap-2">
              <Switch
                checked={filters.hidePrepaid}
                onCheckedChange={(v) => onChange({ ...filters, hidePrepaid: v })}
              />
              <Label>Hide prepaid</Label>
            </div>
          </div>
        </div>

        {/* Term Length Filter */}
        <div className="mt-4 space-y-2">
          <Label>Term Length (months)</Label>
          <div className="flex flex-wrap gap-2">
            {TERM_OPTIONS.map((term) => (
              <Badge
                key={term}
                variant={filters.termLengths.includes(term) ? "default" : "outline"}
                className="cursor-pointer select-none"
                onClick={() => toggleTerm(term)}
              >
                {term} mo
              </Badge>
            ))}
            {filters.termLengths.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 text-xs"
                onClick={() => onChange({ ...filters, termLengths: [] })}
              >
                Clear
              </Button>
            )}
          </div>
        </div>

        <div className="mt-3 text-xs text-muted-foreground">
          Showing {planCount} plans
        </div>
      </CardContent>
    </Card>
  )
}
