import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Activity,
  FlaskConical,
  LayoutDashboard,
  LogOut,
  Menu,
  Server,
  X,
} from 'lucide-react';
import { useApi } from '../hooks/useApi';
import { useBreakpoint } from '../hooks/useBreakpoint';
import { useChatAuth } from '../hooks/useChatAuth';
import LogoPredictfy from './LogoPredictfy';
import './Sidebar.css';

const NAV = [
  { to: '/gestao', label: 'GESTÃO', icon: <LayoutDashboard size={18} strokeWidth={1.7} /> },
  { to: '/monitoramento', label: 'MONITORAMENTO', icon: <Activity size={18} strokeWidth={1.7} /> },
  { to: '/tecnico', label: 'TÉCNICO', icon: <Server size={18} strokeWidth={1.7} /> },
  { to: '/modelos', label: 'MODELOS', icon: <FlaskConical size={18} strokeWidth={1.7} /> },
];

const SIDEBAR_FULL = 232;
const SIDEBAR_COMPACT = 60;

function SidebarInner({
  expanded,
  clock,
  email,
  p2Critical,
  p3Critical,
  kpiDisponivel,
  onLogout,
  onNavClick,
}) {
  let kpiLabel = 'KPIS SINCRONIZANDO';
  let kpiTone = 'neutral';
  if (p2Critical) {
    kpiLabel = 'KPI P2 CRÍTICO';
    kpiTone = 'critical';
  } else if (p3Critical) {
    kpiLabel = 'KPI P3 CRÍTICO';
    kpiTone = 'critical';
  } else if (kpiDisponivel) {
    kpiLabel = 'KPIS DENTRO DA META';
    kpiTone = 'healthy';
  }

  return (
    <>
      <div className="sidebar-brand" aria-label="Predictfy AIOps">
        <span className="sidebar-brand__mark" aria-hidden="true">
          <LogoPredictfy />
        </span>
        <span className="sidebar-brand__copy" aria-hidden={!expanded}>
          <strong>PREDICTFY</strong>
          <small>AIOPS // LOCAWEB</small>
        </span>
      </div>

      <nav className="sidebar-nav" aria-label="Navegação principal">
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavClick}
            aria-label={label}
            title={expanded ? undefined : label}
            className={({ isActive }) => (
              `sidebar-nav__item${isActive ? ' sidebar-nav__item--active' : ''}`
            )}
          >
            <span className="sidebar-nav__icon" aria-hidden="true">
              {icon}
            </span>
            <span className="sidebar-nav__label" aria-hidden="true">{label}</span>
            <span className="sidebar-nav__signal" aria-hidden="true" />
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-telemetry" aria-label="Status operacional">
        <div className="sidebar-telemetry__row">
          <span className="sidebar-online-dot" aria-hidden="true" />
          <span className="sidebar-telemetry__copy" aria-hidden={!expanded}>
            <strong>ONLINE</strong>
            <time>{clock}</time>
          </span>
        </div>
        <div
          className={`sidebar-kpi sidebar-kpi--${kpiTone}`}
          title={expanded ? undefined : kpiLabel}
        >
          <span aria-hidden="true" />
          <small aria-hidden={!expanded}>{kpiLabel}</small>
        </div>
      </div>

      <div className="sidebar-session">
        <div className="sidebar-session__identity" title={expanded ? undefined : email}>
          <span className="sidebar-session__avatar" aria-hidden="true">
            {email?.slice(0, 1).toUpperCase() || 'P'}
          </span>
          <span className="sidebar-session__copy" aria-hidden={!expanded}>
            <small>SESSÃO ATIVA</small>
            <strong>{email}</strong>
          </span>
        </div>
        <button
          type="button"
          className="sidebar-session__logout"
          onClick={onLogout}
          aria-label="Encerrar sessão do Predictfy"
          title={expanded
            ? 'Encerra somente o Predictfy e mantém sua conta Microsoft conectada'
            : 'Encerrar sessão do Predictfy'}
        >
          <span className="sidebar-session__logout-icon" aria-hidden="true">
            <LogOut size={17} strokeWidth={1.7} />
          </span>
          <span className="sidebar-session__logout-label" aria-hidden="true">
            ENCERRAR SESSÃO
          </span>
        </button>
      </div>
    </>
  );
}

export default function Sidebar() {
  const { isMobile, isTablet } = useBreakpoint();
  const { user, logout } = useChatAuth();
  const [clock, setClock] = useState('');
  const [hovered, setHovered] = useState(false);
  const [focusWithin, setFocusWithin] = useState(false);
  const [tabletExpanded, setTabletExpanded] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const expanded = hovered || focusWithin || tabletExpanded;

  const { data: kpiData, disponivel: kpiDisponivel } = useApi('/kpi');

  useEffect(() => {
    document.documentElement.style.setProperty(
      '--sidebar-width',
      isMobile ? '0px' : `${SIDEBAR_COMPACT}px`,
    );
  }, [isMobile]);

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('pt-BR', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    }));
    tick();
    const id = window.setInterval(tick, 1_000);
    return () => window.clearInterval(id);
  }, []);

  const p2Critical = kpiDisponivel
    ? kpiData?.P2?.tendencia === 'critico' || kpiData?.P2?.margemRestante < 0
    : false;
  const p3Critical = kpiDisponivel
    ? kpiData?.P3?.tendencia === 'critico' || kpiData?.P3?.margemRestante < 0
    : false;

  const innerProps = {
    clock,
    email: user.email,
    p2Critical,
    p3Critical,
    kpiDisponivel,
    onLogout: logout,
  };

  if (isMobile) {
    return (
      <>
        <button
          type="button"
          className="sidebar-mobile-trigger"
          onClick={() => setMobileOpen((current) => !current)}
          aria-expanded={mobileOpen}
          aria-controls="predictfy-mobile-navigation"
          aria-label={mobileOpen ? 'Fechar navegação' : 'Abrir navegação'}
        >
          {mobileOpen ? <X size={19} /> : <Menu size={19} />}
        </button>

        {mobileOpen ? (
          <button
            type="button"
            className="sidebar-mobile-backdrop"
            onClick={() => setMobileOpen(false)}
            aria-label="Fechar navegação"
          />
        ) : null}

        <aside
          id="predictfy-mobile-navigation"
          className={`sidebar sidebar--mobile${mobileOpen ? ' sidebar--mobile-open' : ''}`}
          style={{ '--sidebar-expanded-width': `${SIDEBAR_FULL}px` }}
          aria-hidden={!mobileOpen}
          inert={!mobileOpen}
        >
          <SidebarInner
            {...innerProps}
            expanded
            onNavClick={() => setMobileOpen(false)}
          />
        </aside>
      </>
    );
  }

  return (
    <aside
      className={`sidebar ${expanded ? 'sidebar--expanded' : 'sidebar--compact'}`}
      style={{ '--sidebar-expanded-width': `${SIDEBAR_FULL}px` }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onFocusCapture={() => setFocusWithin(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setFocusWithin(false);
      }}
      onPointerDown={(event) => {
        if (isTablet && event.pointerType === 'touch' && !expanded) {
          event.preventDefault();
          setTabletExpanded(true);
        }
      }}
      data-expanded={expanded}
      aria-label="Barra lateral Predictfy"
    >
      <SidebarInner
        {...innerProps}
        expanded={expanded}
        onNavClick={isTablet ? () => setTabletExpanded(false) : undefined}
      />
    </aside>
  );
}
