# Quick Task Research: Add Collapsible Sidebar and EFL Results Page

**Researched:** 2026-03-22
**Domain:** React UI routing and component architecture
**Confidence:** HIGH

## Summary

The current UI is a **single-page React app with NO routing library**. It uses shadcn/ui components with Tailwind CSS v4.2.1 and has sidebar theming already defined in CSS. To add navigation, we need to:

1. Install `react-router-dom` for routing
2. Create layout component with collapsible sidebar
3. Create new EFL Results page component
4. Update App.tsx to use routing

**Primary recommendation:** Use react-router-dom v7 + shadcn sidebar pattern with the existing sidebar CSS variables already defined.

## Current Architecture

### Tech Stack
| Technology | Version | Current Use |
|------------|---------|-------------|
| React | 19.2.4 | Core framework |
| Vite | 8.0.0 | Build tool |
| Tailwind CSS | 4.2.1 | Styling (with @tailwindcss/vite plugin) |
| shadcn/ui | 4.0.7 | Component library |
| lucide-react | 0.577.0 | Icons |
| @tanstack/react-table | 8.21.3 | Table component (used in PlanTable) |
| **NO ROUTER** | — | Single page app currently |

### Project Structure
```
ui/src/
├── main.tsx                    # Entry point
├── App.tsx                     # Main component (plan browser)
├── index.css                   # Global styles + theme
├── components/
│   ├── FilterControls.tsx      # Search/filter UI
│   ├── PlanTable.tsx           # Plans table with tanstack/react-table
│   ├── columns.tsx             # Table column definitions
│   └── ui/                     # shadcn components
│       ├── button.tsx
│       ├── table.tsx
│       ├── input.tsx
│       ├── badge.tsx
│       ├── select.tsx
│       ├── slider.tsx
│       ├── label.tsx
│       ├── switch.tsx
│       ├── card.tsx
│       └── separator.tsx
├── lib/
│   ├── api.ts                  # API calls (fetchPlans)
│   └── utils.ts                # shadcn utils (cn function)
└── types/
    └── plan.ts                 # Plan interface
```

### Current App Structure
- **Single page**: App.tsx renders everything (header + FilterControls + PlanTable)
- **No layout component**: Header is inline in App.tsx
- **State management**: useState for filters, plans, loading, error
- **API proxy**: Vite proxies /api to localhost:8000
- **Base path**: Uses `/PowerToChoose/` in production (GitHub Pages)

### Styling Approach
- **Tailwind CSS v4.2.1** with @tailwindcss/vite plugin
- **shadcn/ui** component system (class-variance-authority + clsx + tailwind-merge)
- **CSS variables** for theming (light/dark mode via prefers-color-scheme)
- **Sidebar CSS variables already defined** in index.css:
  - `--sidebar`, `--sidebar-foreground`, `--sidebar-primary`, etc.
  - Ready for use, just needs implementation

## Required Changes

### 1. Install React Router
```bash
npm install react-router-dom@7
npm install --save-dev @types/react-router-dom
```

**Version note:** react-router-dom v7 is current stable (as of March 2026).

### 2. Create Layout Component with Sidebar

**Pattern:** Create `src/components/Layout.tsx` with:
- Collapsible sidebar (toggle button, nav items)
- Main content area with <Outlet /> for routed pages
- Use existing `--sidebar-*` CSS variables
- Use lucide-react icons (Menu, Home, FileText, etc.)

**Key considerations:**
- Sidebar state persisted in localStorage or context
- Responsive: mobile (overlay), desktop (inline collapsible)
- Match existing shadcn theming

### 3. Routing Structure

```tsx
// main.tsx
<BrowserRouter basename="/PowerToChoose/">
  <Routes>
    <Route element={<Layout />}>
      <Route path="/" element={<PlanBrowser />} />
      <Route path="/efl-results" element={<EFLResults />} />
    </Route>
  </Routes>
</BrowserRouter>
```

**Pages:**
- `/` - Plan Browser (current App.tsx content)
- `/efl-results` - New EFL Results page

### 4. Component Refactoring

| Current | New Structure |
|---------|---------------|
| App.tsx (everything) | Layout.tsx (shell) + PlanBrowser.tsx (current App content) + EFLResults.tsx (new page) |
| No navigation | Sidebar with nav items |
| Single page | Multi-page with routing |

## Architecture Patterns

### Pattern 1: shadcn Sidebar (Recommended)

**Structure:**
```tsx
// components/Layout.tsx
<div className="flex h-screen">
  <aside className={cn(
    "bg-sidebar border-r border-sidebar-border transition-all",
    collapsed ? "w-16" : "w-64"
  )}>
    <nav>
      <Link to="/">...</Link>
      <Link to="/efl-results">...</Link>
    </nav>
  </aside>
  <main className="flex-1 overflow-auto">
    <Outlet />
  </main>
</div>
```

**Benefits:**
- Uses existing CSS variables
- Matches shadcn patterns
- Simple, no external sidebar library needed

### Pattern 2: Navigation Items

```tsx
const navItems = [
  { path: "/", label: "Plan Browser", icon: Home },
  { path: "/efl-results", label: "EFL Results", icon: FileText },
]
```

### Anti-Patterns to Avoid
- **Don't use hash routing (#/)** - production uses /PowerToChoose/ base path, needs BrowserRouter
- **Don't create separate theme system** - use existing CSS variables
- **Don't nest routes deeply** - keep flat (both pages are top-level)

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Routing | Manual path matching with state | react-router-dom | Industry standard, handles history, params, nested routes |
| Class merging | Manual className logic | cn() from lib/utils.ts | Already in project, handles conditional classes safely |
| Sidebar state | Props drilling | localStorage + useState | Simple persistence, no context needed for 2 pages |

## Code Examples

### Example 1: Router Setup (main.tsx)
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import Layout from './components/Layout'
import PlanBrowser from './pages/PlanBrowser'
import EFLResults from './pages/EFLResults'

const basename = import.meta.env.PROD ? '/PowerToChoose/' : '/'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter basename={basename}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<PlanBrowser />} />
          <Route path="/efl-results" element={<EFLResults />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
```

### Example 2: Layout Component Pattern
```tsx
// components/Layout.tsx
import { useState } from 'react'
import { Outlet, Link, useLocation } from 'react-router-dom'
import { Menu, Home, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  return (
    <div className="flex h-screen">
      <aside className={cn(
        "bg-sidebar border-r border-sidebar-border transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}>
        <div className="p-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed(!collapsed)}
          >
            <Menu />
          </Button>
        </div>
        <nav className="space-y-2 p-2">
          <Link
            to="/"
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2",
              "hover:bg-sidebar-accent",
              location.pathname === '/' && "bg-sidebar-accent"
            )}
          >
            <Home className="h-5 w-5" />
            {!collapsed && <span>Plan Browser</span>}
          </Link>
          <Link
            to="/efl-results"
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2",
              "hover:bg-sidebar-accent",
              location.pathname === '/efl-results' && "bg-sidebar-accent"
            )}
          >
            <FileText className="h-5 w-5" />
            {!collapsed && <span>EFL Results</span>}
          </Link>
        </nav>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
```

### Example 3: Refactored Page Component
```tsx
// pages/PlanBrowser.tsx
// Move entire App.tsx content here (FilterControls + PlanTable)
// Replace outer <div> with appropriate page wrapper
// Keep all existing logic, just extract from App.tsx
```

## Common Pitfalls

### Pitfall 1: Base Path Mismatch
**What goes wrong:** Routing works locally but breaks on GitHub Pages
**Why it happens:** vite.config.ts sets base: "/PowerToChoose/" in production, router must match
**How to avoid:** Use `basename` prop in BrowserRouter with same value as vite base
**Warning signs:** Links work in dev but return 404 on deployed site

### Pitfall 2: Missing Outlet in Layout
**What goes wrong:** Nested routes don't render
**Why it happens:** react-router needs <Outlet /> to render child routes
**How to avoid:** Always include <Outlet /> in layout component
**Warning signs:** Layout renders but page content is blank

### Pitfall 3: Sidebar CSS Variable References
**What goes wrong:** Sidebar colors don't match theme
**Why it happens:** Using hardcoded colors instead of CSS variables
**How to avoid:** Use `bg-sidebar`, `text-sidebar-foreground`, etc. Tailwind classes
**Warning signs:** Sidebar looks wrong in dark mode

## Open Questions

None — architecture is straightforward. All patterns exist in current codebase.

## Sources

### Primary (HIGH confidence)
- ui/package.json - Dependencies verified (no router currently)
- ui/src/App.tsx - Current single-page structure
- ui/src/index.css - Sidebar CSS variables already defined (lines 34-41, 70-77)
- ui/vite.config.ts - Base path configuration (/PowerToChoose/)
- shadcn/ui component patterns - Already in use throughout codebase

### Secondary (MEDIUM confidence)
- react-router-dom v7 documentation - Current stable version (March 2026)

## Metadata

**Confidence breakdown:**
- Current architecture: HIGH - directly observed from codebase
- Routing approach: HIGH - react-router-dom is standard, version verified
- Sidebar pattern: HIGH - CSS variables already exist, shadcn patterns in use

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (30 days - stable stack)
