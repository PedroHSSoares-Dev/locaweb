import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import { DashboardProvider } from './context/DashboardContext';
import Sidebar from './components/Sidebar';
import GestaoPage from './pages/GestaoPage';
import MonitoramentoPage from './pages/MonitoramentoPage';
import TecnicoPage from './pages/TecnicoPage';
import { useBreakpoint } from './hooks/useBreakpoint';

import { Analytics } from "@vercel/analytics/react"

function AppInner() {
  const { isMobile } = useBreakpoint();
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100%', overflow: 'hidden' }}>
      <Sidebar />
      <div style={{
        flex: 1,
        minWidth: 0,
        marginLeft: isMobile ? 0 : 'var(--sidebar-width)',
        paddingTop: isMobile ? 48 : 0,
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflowY: 'auto',
        overflowX: 'hidden',
        transition: 'margin-left 0.25s cubic-bezier(0.4,0,0.2,1)',
      }}>
            <Routes>
              <Route path="/" element={<Navigate to="/gestao" replace />} />
              <Route path="/gestao"        element={<GestaoPage />} />
              <Route path="/monitoramento" element={<MonitoramentoPage />} />
              <Route path="/tecnico"       element={<TecnicoPage />} />
            </Routes>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <DashboardProvider>
      <BrowserRouter>
        <AppInner />
        <Analytics />
      </BrowserRouter>
    </DashboardProvider>
  );
}
