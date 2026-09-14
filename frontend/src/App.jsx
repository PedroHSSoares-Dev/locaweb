import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import './index.css';
import { DashboardProvider } from './context/DashboardContext';
import Sidebar from './components/Sidebar';
import { useBreakpoint } from './hooks/useBreakpoint';
import { useChatAuth } from './hooks/useChatAuth';
import { isAdminUser } from './auth/authorization';
import LogoPredictfy from './components/LogoPredictfy';
import './App.css';

import { Analytics } from "@vercel/analytics/react"

const GestaoPage = lazy(() => import('./pages/GestaoPage'));
const MonitoramentoPage = lazy(() => import('./pages/MonitoramentoPage'));
const TecnicoPage = lazy(() => import('./pages/TecnicoPage'));
const ModelosPage = lazy(() => import('./pages/ModelosPage'));
const OperationsPage = lazy(() => import('./pages/OperationsPage'));
const AdminPage = lazy(() => import('./pages/AdminPage'));
const ChatBot = lazy(() => import('./components/ChatBot'));

function RouteFallback() {
  return (
    <div className="route-fallback" role="status" aria-live="polite">
      <span className="route-fallback__pulse" aria-hidden="true" />
      Carregando área…
    </div>
  );
}

function AppInner() {
  const { isMobile } = useBreakpoint();
  const { user } = useChatAuth();
  return (
    <div className="app-shell">
      <Sidebar />
      <div className={`app-main${isMobile ? ' app-main--mobile' : ''}`}>
            <Suspense fallback={<RouteFallback />}>
              <Routes>
                <Route path="/" element={<Navigate to="/gestao" replace />} />
                <Route path="/gestao"        element={<GestaoPage />} />
                <Route path="/monitoramento" element={<MonitoramentoPage />} />
                <Route path="/operacoes" element={<OperationsPage />} />
                <Route path="/tecnico"       element={<TecnicoPage />} />
                <Route path="/modelos"       element={<ModelosPage />} />
                <Route
                  path="/admin"
                  element={isAdminUser(user) ? <AdminPage /> : <Navigate to="/gestao" replace />}
                />
                <Route path="*" element={<Navigate to="/gestao" replace />} />
              </Routes>
            </Suspense>
      </div>
      <Suspense fallback={null}>
        <ChatBot />
      </Suspense>
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
        <aside className="login-card__evaluator" aria-label="Orientação para professores avaliadores">
          <span aria-hidden="true">FIAP</span>
          <p>
            <strong>Professor(a) avaliador(a)?</strong>
            Entre com seu e-mail institucional da FIAP para acessar e avaliar o projeto.
          </p>
        </aside>
        {error && <div className="login-card__error" role="alert">{error}</div>}
        {!entraConfigured && <small>Configuração local pendente: IDs públicos do Entra ainda não informados.</small>}
        <div className="login-card__security">
          <span>IDENTIDADE / MICROSOFT ENTRA ID</span>
          <span>ACESSO / DIRETÓRIO RBAC</span>
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
