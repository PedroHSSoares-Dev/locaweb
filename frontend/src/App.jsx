import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import { DashboardProvider } from './context/DashboardContext';
import Sidebar from './components/Sidebar';
import ChatBot from './components/ChatBot';
import GestaoPage from './pages/GestaoPage';
import MonitoramentoPage from './pages/MonitoramentoPage';
import TecnicoPage from './pages/TecnicoPage';
import ModelosPage from './pages/ModelosPage';
import { useBreakpoint } from './hooks/useBreakpoint';
import { useChatAuth } from './hooks/useChatAuth';
import LogoPredictfy from './components/LogoPredictfy';
import './App.css';

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
        background: 'var(--bg)',
      }}>
            <Routes>
              <Route path="/" element={<Navigate to="/gestao" replace />} />
              <Route path="/gestao"        element={<GestaoPage />} />
              <Route path="/monitoramento" element={<MonitoramentoPage />} />
              <Route path="/tecnico"       element={<TecnicoPage />} />
              <Route path="/modelos"       element={<ModelosPage />} />
            </Routes>
      </div>
      <ChatBot />
    </div>
  );
}

function LoginScreen() {
  const { status, error, signIn, entraConfigured } = useChatAuth();
  const loading = status === 'verifying' || status === 'checking';
  return (
    <main className="login-screen">
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-card__mark"><LogoPredictfy size={30} color="var(--purple)" /></div>
        <div className="login-card__eyebrow">PREDICTFY × LOCAWEB</div>
        <h1 id="login-title">Acesso operacional protegido</h1>
        <p>Entre com a conta Microsoft autorizada para acessar a dashboard e o assistente AIOps.</p>
        <button className="microsoft-login" type="button" onClick={signIn} disabled={loading || !entraConfigured}>
          <span className="microsoft-login__logo" aria-hidden="true"><i /><i /><i /><i /></span>
          {loading ? 'VALIDANDO IDENTIDADE…' : 'ENTRAR COM MICROSOFT'}
        </button>
        {error && <div className="login-card__error" role="alert">{error}</div>}
        {!entraConfigured && <small>Configuração local pendente: IDs públicos do Entra ainda não informados.</small>}
        <div className="login-card__security">
          <span>IDENTIDADE / MICROSOFT ENTRA ID</span>
          <span>ACESSO / ALLOWLIST</span>
        </div>
      </section>
    </main>
  );
}

export default function App() {
  const { user } = useChatAuth();
  return (
    <DashboardProvider>
      <BrowserRouter>
        {user ? <AppInner /> : <LoginScreen />}
        <Analytics />
      </BrowserRouter>
    </DashboardProvider>
  );
}
