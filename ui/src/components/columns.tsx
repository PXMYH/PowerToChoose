import { type ColumnDef } from "@tanstack/react-table"
import { ArrowUpDown } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { Plan } from "@/types/plan"

function SortHeader({
  column,
  label,
}: {
  column: { toggleSorting: (desc?: boolean) => void; getIsSorted: () => string | false }
  label: string
}) {
  return (
    <Button
      variant="ghost"
      size="sm"
      className="-ml-3 h-8"
      onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
    >
      {label}
      <ArrowUpDown className="ml-1 h-3 w-3" />
    </Button>
  )
}

export const columns: ColumnDef<Plan>[] = [
  {
    accessorKey: "company_name",
    header: ({ column }) => <SortHeader column={column} label="Company" />,
    cell: ({ row }) => {
      const logo = row.original.company_logo
      const name = row.getValue<string>("company_name")
      return (
        <div className="flex items-center gap-2 min-w-[140px]">
          {logo && (
            <img
              src={logo}
              alt={name}
              className="h-6 w-12 object-contain shrink-0"
              onError={(e) => { e.currentTarget.style.display = "none" }}
            />
          )}
          <span className="text-sm font-medium truncate">{name}</span>
        </div>
      )
    },
  },
  {
    accessorKey: "plan_name",
    header: ({ column }) => <SortHeader column={column} label="Plan" />,
    cell: ({ row }) => (
      <span className="text-sm truncate max-w-[200px] block">
        {row.getValue<string>("plan_name")}
      </span>
    ),
  },
  {
    accessorKey: "term_value",
    header: ({ column }) => <SortHeader column={column} label="Term" />,
    cell: ({ row }) => (
      <span className="text-sm">{row.getValue<number>("term_value")} mo</span>
    ),
  },
  {
    accessorKey: "rate_type",
    header: "Rate",
    cell: ({ row }) => {
      const type = row.getValue<string>("rate_type")
      return (
        <Badge variant={type === "Fixed" ? "default" : "secondary"}>
          {type}
        </Badge>
      )
    },
  },
  {
    accessorKey: "price_kwh500",
    header: ({ column }) => <SortHeader column={column} label="500 kWh" />,
    cell: ({ row }) => (
      <span className="text-sm font-mono">
        {row.getValue<number>("price_kwh500")}¢
      </span>
    ),
  },
  {
    accessorKey: "price_kwh1000",
    header: ({ column }) => <SortHeader column={column} label="1000 kWh" />,
    cell: ({ row }) => (
      <span className="text-sm font-mono font-semibold">
        {row.getValue<number>("price_kwh1000")}¢
      </span>
    ),
  },
  {
    accessorKey: "price_kwh2000",
    header: ({ column }) => <SortHeader column={column} label="2000 kWh" />,
    cell: ({ row }) => (
      <span className="text-sm font-mono">
        {row.getValue<number>("price_kwh2000")}¢
      </span>
    ),
  },
  {
    accessorKey: "renewable_energy_description",
    header: ({ column }) => <SortHeader column={column} label="Renewable" />,
    cell: ({ row }) => {
      const desc = row.getValue<string>("renewable_energy_description")
      const pct = parseInt(desc) || 0
      return (
        <Badge variant={pct === 100 ? "default" : "outline"} className={pct === 100 ? "bg-green-600" : ""}>
          {desc}
        </Badge>
      )
    },
  },
  {
    accessorKey: "prepaid",
    header: "Prepaid",
    cell: ({ row }) =>
      row.getValue<boolean>("prepaid") ? (
        <Badge variant="secondary">Yes</Badge>
      ) : null,
  },
]
