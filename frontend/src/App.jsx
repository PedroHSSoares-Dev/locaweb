import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import { DashboardProvider } from './context/DashboardContext';
import Sidebar from './components/Sidebar';
import GestaoPage from './pages/GestaoPage';
import MonitoramentoPage from './pages/MonitoramentoPage';
import TecnicoPage from './pages/TecnicoPage';

import { Analytics } from "@vercel/analytics/react"

export default function App() {
  return (
    <DashboardProvider>
      <BrowserRouter>
        <div style={{
          display: 'flex',
          height: '100vh',
          width: '100%',
          overflow: 'hidden',
        }}>
          <Sidebar />
          <div style={{
            flex: 1,
            minWidth: 0,
            marginLeft: 'var(--sidebar-width)',
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
        <Analytics />
      </BrowserRouter>
    </DashboardProvider>
  );
}
