import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getExpandedRowModel,
  useReactTable,
  type SortingState,
  type ColumnFiltersState,
  type ExpandedState,
} from "@tanstack/react-table"
import { useState } from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { columns } from "@/components/columns"
import type { Plan } from "@/types/plan"

interface PlanTableProps {
  data: Plan[]
}

function PlanDetail({ plan }: { plan: Plan }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-muted/50 text-sm">
      <div className="space-y-2">
        <h4 className="font-semibold">Plan Details</h4>
        {plan.special_terms && (
          <p className="text-muted-foreground text-xs leading-relaxed">
            {plan.special_terms}
          </p>
        )}
        {plan.pricing_details && (
          <p className="text-xs">
            <span className="font-medium">Pricing: </span>
            {plan.pricing_details}
          </p>
        )}
        <div className="flex gap-2 flex-wrap">
          {plan.new_customer && <Badge variant="outline">New customers</Badge>}
          {plan.timeofuse && <Badge variant="outline">Time of use</Badge>}
          {plan.minimum_usage && <Badge variant="outline">Min usage</Badge>}
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="font-semibold">Documents</h4>
        <div className="flex flex-col gap-1">
          {plan.fact_sheet && (
            <a
              href={plan.fact_sheet}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline text-xs"
            >
              Electricity Facts Label (EFL)
            </a>
          )}
          {plan.terms_of_service && (
            <a
              href={plan.terms_of_service}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline text-xs"
            >
              Terms of Service
            </a>
          )}
          {plan.go_to_plan && (
            <a
              href={plan.go_to_plan}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline text-xs font-medium"
            >
              Enroll / Plan Page
            </a>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="font-semibold">Contact</h4>
        {plan.enroll_phone && (
          <p className="text-xs">
            <span className="font-medium">Phone: </span>
            <a href={`tel:${plan.enroll_phone}`} className="text-blue-600">
              {plan.enroll_phone}
            </a>
          </p>
        )}
        {plan.website && (
          <a
            href={plan.website.startsWith("http") ? plan.website : `https://${plan.website}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline text-xs"
          >
            Company Website
          </a>
        )}
        <Separator className="my-2" />
        <div className="flex gap-4 text-xs text-muted-foreground">
          <span>Rating: {plan.rating_total}/5 ({plan.rating_count})</span>
        </div>
      </div>
    </div>
  )
}

export function PlanTable({ data }: PlanTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: "price_kwh1000", desc: false },
  ])
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([])
  const [expanded, setExpanded] = useState<ExpandedState>({})

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onExpandedChange: setExpanded,
    state: { sorting, columnFilters, expanded },
  })

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead key={header.id}>
                  {header.isPlaceholder
                    ? null
                    : flexRender(header.column.columnDef.header, header.getContext())}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {table.getRowModel().rows.length ? (
            table.getRowModel().rows.map((row) => (
              <>
                <TableRow key={row.id} className="cursor-pointer" onClick={() => row.toggleExpanded()}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
                {row.getIsExpanded() && (
                  <TableRow key={`${row.id}-detail`}>
                    <TableCell colSpan={columns.length} className="p-0">
                      <PlanDetail plan={row.original} />
                    </TableCell>
                  </TableRow>
                )}
              </>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length} className="h-24 text-center">
                No plans found.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      <div className="p-2 text-xs text-muted-foreground text-right">
        {table.getFilteredRowModel().rows.length} plans
      </div>
    </div>
  )
}
