import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useApi } from '../hooks/useApi';
import { useBreakpoint } from '../hooks/useBreakpoint';
import LogoPredictfy from './LogoPredictfy';
import { LayoutDashboard, Activity, Server } from 'lucide-react';

const NAV = [
  { to: '/gestao',        label: 'GESTÃO',       icon: <LayoutDashboard size={18} /> },
  { to: '/monitoramento', label: 'MONITORAMENTO', icon: <Activity size={18} /> },
  { to: '/tecnico',       label: 'TÉCNICO',       icon: <Server size={18} /> },
];

const SIDEBAR_FULL      = 220;
const SIDEBAR_COLLAPSED = 52;

// ─── Conteúdo interno da sidebar (reutilizado em mobile e desktop) ────────────
function SidebarInner({ collapsed, onToggle, clock, p2Critical, p3Critical, kpiDisponivel, onNavClick }) {
  return (
    <>
      {/* ── Logo ── */}
      <div
        onClick={onToggle}
        style={{
          padding: collapsed ? '20px 0 18px' : '20px 20px 18px',
          borderBottom: '1px solid var(--border)',
          cursor: onToggle ? 'pointer' : 'default',
          display: 'flex', alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          gap: collapsed ? 0 : 10,
          userSelect: 'none',
          transition: 'padding 0.25s ease',
        }}
      >
        <div style={{
          width: 24, height: 24, color: 'var(--teal)',
          flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <LogoPredictfy />
        </div>
        <div style={{
          overflow: 'hidden', opacity: collapsed ? 0 : 1,
          width: collapsed ? 0 : 'auto',
          transition: 'opacity 0.2s ease, width 0.25s ease', whiteSpace: 'nowrap',
        }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color: 'var(--teal)', letterSpacing: '0.1em' }}>
            PREDICTFY
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)', letterSpacing: '0.08em', marginTop: 2 }}>
            AIOPS // LOCAWEB
          </div>
        </div>
      </div>

      {/* ── Nav ── */}
      <nav style={{ flex: 1, padding: '10px 0' }}>
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to} to={to}
            onClick={onNavClick}
            title={collapsed ? label : undefined}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              gap: collapsed ? 0 : 10,
              padding: collapsed ? '12px 0' : '10px 20px',
              textDecoration: 'none',
              fontFamily: 'var(--font-mono)', fontSize: 12,
              fontWeight: isActive ? 600 : 400, letterSpacing: '0.1em',
              color: isActive ? 'var(--teal)' : 'var(--text-sec)',
              background: isActive ? 'var(--teal-dim)' : 'transparent',
              borderLeft: `2px solid ${isActive ? 'var(--teal)' : 'transparent'}`,
              transition: 'all 0.15s', overflow: 'hidden', whiteSpace: 'nowrap',
            })}
          >
            <div style={{ width: 24, display: 'flex', justifyContent: 'center', flexShrink: 0 }}>
              {icon}
            </div>
            <span style={{
              opacity: collapsed ? 0 : 1,
              width: collapsed ? 0 : 'auto',
              transition: 'opacity 0.2s ease, width 0.25s ease',
              overflow: 'hidden',
            }}>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* ── Footer ── */}
      <div style={{
        padding: collapsed ? '14px 0' : '14px 20px',
        borderTop: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        alignItems: collapsed ? 'center' : 'flex-start',
        gap: 6, transition: 'padding 0.25s ease',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: collapsed ? 0 : 10 }}>
          <div style={{ width: 24, display: 'flex', justifyContent: 'center', alignItems: 'center', flexShrink: 0 }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%',
              background: 'var(--green)', display: 'inline-block',
              animation: 'pulse-dot 2s ease infinite', flexShrink: 0,
            }} />
          </div>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--green)', letterSpacing: '0.1em',
            opacity: collapsed ? 0 : 1, width: collapsed ? 0 : 'auto',
            overflow: 'hidden', transition: 'opacity 0.2s ease, width 0.25s ease', whiteSpace: 'nowrap',
          }}>ONLINE</span>
        </div>

        {!collapsed && (
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)', marginLeft: 34 }}>
            {clock}
          </div>
        )}

        {!collapsed && p2Critical && (
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--red)', letterSpacing: '0.06em',
            marginLeft: 34, animation: 'pulse-dot 2s ease infinite',
          }}>⚠ KPI P2 CRÍTICO</div>
        )}
        {!collapsed && p3Critical && (
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--red)', letterSpacing: '0.06em',
            marginLeft: 34, animation: 'pulse-dot 2s ease infinite',
          }}>⚠ KPI P3 CRÍTICO</div>
        )}
        {!collapsed && kpiDisponivel && !p2Critical && !p3Critical && (
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--green)', letterSpacing: '0.06em',
            marginLeft: 34,
          }}>✓ KPI DENTRO DA META</div>
        )}
      </div>
    </>
  );
}

// ─── Sidebar principal ────────────────────────────────────────────────────────
export default function Sidebar() {
  const { isMobile, isTablet } = useBreakpoint();
  const location = useLocation();
  const [clock, setClock]         = useState('');
  const [collapsed, setCollapsed] = useState(() => {
    const w = window.innerWidth;
    const isTab = w >= 768 && w < 1024;
    const sidebarW = w < 768 ? 0 : isTab ? SIDEBAR_COLLAPSED : SIDEBAR_FULL;
    document.documentElement.style.setProperty('--sidebar-width', `${sidebarW}px`);
    return isTab;
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  const { data: kpiData, disponivel: kpiDisponivel } = useApi('/kpi');

  // Fechar sidebar mobile ao navegar
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // Tablet → colapsar; desktop → expandir
  useEffect(() => {
    if (isTablet) setCollapsed(true);
    if (!isTablet && !isMobile) setCollapsed(false);
  }, [isTablet, isMobile]);

  // Sincronizar CSS var
  useEffect(() => {
    if (isMobile) {
      document.documentElement.style.setProperty('--sidebar-width', '0px');
    } else {
      document.documentElement.style.setProperty(
        '--sidebar-width',
        collapsed ? `${SIDEBAR_COLLAPSED}px` : `${SIDEBAR_FULL}px`
      );
    }
  }, [collapsed, isMobile]);

  // Relógio
  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('pt-BR', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const p2Critical = kpiDisponivel
    ? kpiData?.P2?.tendencia === 'critico' || kpiData?.P2?.margemRestante < 0
    : false;
  const p3Critical = kpiDisponivel
    ? kpiData?.P3?.tendencia === 'critico' || kpiData?.P3?.margemRestante < 0
    : false;

  // ── Mobile: hambúrguer + drawer deslizante ────────────────────────────────
  if (isMobile) {
    return (
      <>
        <button
          onClick={() => setMobileOpen(o => !o)}
          style={{
            position: 'fixed', top: 12, left: 12, zIndex: 200,
            background: 'var(--surface2)', border: '1px solid var(--border-md)',
            borderRadius: 6, padding: '8px 10px',
            cursor: 'pointer', color: 'var(--teal)',
            fontFamily: 'var(--font-mono)', fontSize: 16,
          }}
        >
          {mobileOpen ? '✕' : '☰'}
        </button>

        {mobileOpen && (
          <div
            onClick={() => setMobileOpen(false)}
            style={{ position: 'fixed', inset: 0, zIndex: 150, background: 'rgba(0,0,0,0.6)' }}
          />
        )}

        <aside style={{
          position: 'fixed', top: 0, left: 0, zIndex: 160,
          width: SIDEBAR_FULL, height: '100vh',
          background: 'var(--surface1)', borderRight: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column',
          transform: mobileOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 0.25s cubic-bezier(0.4,0,0.2,1)',
        }}>
          <SidebarInner
            collapsed={false} onToggle={null} clock={clock}
            p2Critical={p2Critical} p3Critical={p3Critical}
            kpiDisponivel={kpiDisponivel}
            onNavClick={() => setMobileOpen(false)}
          />
        </aside>
      </>
    );
  }

  // ── Tablet / Desktop: sidebar fixa colapsável ─────────────────────────────
  const w = collapsed ? SIDEBAR_COLLAPSED : SIDEBAR_FULL;

  return (
    <aside style={{
      width: w, height: '100vh',
      background: 'var(--surface1)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      flexShrink: 0, position: 'fixed', top: 0, left: 0, zIndex: 100,
      transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1)', overflow: 'hidden',
    }}>
      <SidebarInner
        collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} clock={clock}
        p2Critical={p2Critical} p3Critical={p3Critical}
        kpiDisponivel={kpiDisponivel}
        onNavClick={null}
      />
    </aside>
  );
}
