import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import { DashboardProvider } from './context/DashboardContext';
import Topbar from './components/Topbar';
import GestaoPage from './pages/GestaoPage';
import MonitoramentoPage from './pages/MonitoramentoPage';
import TecnicoPage from './pages/TecnicoPage';
import FinancialPage from './pages/FinancialPage';

export default function App() {
  return (
    <DashboardProvider>
      <BrowserRouter>
        <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
          <Topbar />
          <Routes>
            <Route path="/" element={<Navigate to="/gestao" replace />} />
            <Route path="/gestao"        element={<GestaoPage />} />
            <Route path="/monitoramento" element={<MonitoramentoPage />} />
            <Route path="/tecnico"       element={<TecnicoPage />} />
            <Route path="/financeiro"    element={<FinancialPage />} />
          </Routes>
        </div>
      </BrowserRouter>
    </DashboardProvider>
  );
}
