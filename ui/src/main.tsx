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
