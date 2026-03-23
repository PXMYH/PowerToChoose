import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import Layout from './components/Layout'
import PlanBrowser from './pages/PlanBrowser'
import EFLResults from './pages/EFLResults'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<PlanBrowser />} />
          <Route path="/efl-results" element={<EFLResults />} />
        </Route>
      </Routes>
    </HashRouter>
  </StrictMode>,
)
