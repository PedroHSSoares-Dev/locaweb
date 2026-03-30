import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { violacoesReais2025, olaTargets } from '../data/mockData';
import LogoPredictfy from './LogoPredictfy';
import { LayoutDashboard, Activity, Server } from 'lucide-react';

const NAV = [
  { to: '/gestao', label: 'GESTÃO', icon: <LayoutDashboard size={18} /> },
  { to: '/monitoramento', label: 'MONITORAMENTO', icon: <Activity size={18} /> },
  { to: '/tecnico', label: 'TÉCNICO', icon: <Server size={18} /> },
];

const SIDEBAR_FULL = 220;
const SIDEBAR_COLLAPSED = 52;

export default function Sidebar() {
  const [clock, setClock] = useState('');
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('pt-BR', {
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    document.documentElement.style.setProperty(
      '--sidebar-width',
      collapsed ? `${SIDEBAR_COLLAPSED}px` : `${SIDEBAR_FULL}px`
    );
  }, [collapsed]);

  const p2Critical = violacoesReais2025.P2 > olaTargets.P2.metaViolacoesAno.max;
  const w = collapsed ? SIDEBAR_COLLAPSED : SIDEBAR_FULL;

  return (
    <aside style={{
      width: w,
      height: '100vh',
      background: 'var(--surface1)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      flexShrink: 0,
      position: 'fixed',
      top: 0, left: 0,
      zIndex: 100,
      transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1)',
      overflow: 'hidden',
    }}>

      {/* ── Logo — clicável para colapsar ─────────────────────────────────── */}
      <div
        onClick={() => setCollapsed(c => !c)}
        style={{
          padding: collapsed ? '20px 0 18px' : '20px 20px 18px',
          borderBottom: '1px solid var(--border)',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          gap: collapsed ? 0 : 10, // <-- ALTERE AQUI: Remova o "10" e coloque esta condição
          userSelect: 'none',
          transition: 'padding 0.25s ease',
        }}
      >
        {/* --- LOGO SVG AQUI --- */}
        <div style={{
          width: 24,             // Largura fixa para a "coluna" do ícone
          height: 24,
          color: 'var(--teal)',
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center' // Centraliza o SVG dentro dos 24px
        }}>
          <LogoPredictfy />
        </div>

        <div style={{
          overflow: 'hidden',
          opacity: collapsed ? 0 : 1,
          width: collapsed ? 0 : 'auto',
          transition: 'opacity 0.2s ease, width 0.25s ease',
          whiteSpace: 'nowrap',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700,
            color: 'var(--teal)', letterSpacing: '0.1em',
          }}>PREDICTFY</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--text-sec)', letterSpacing: '0.08em', marginTop: 2,
          }}>AIOPS // LOCAWEB</div>
        </div>
      </div>

      {/* ── Nav ───────────────────────────────────────────────────────────── */}
      <nav style={{ flex: 1, padding: '10px 0' }}>
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            title={collapsed ? label : undefined}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              justifyContent: collapsed ? 'center' : 'flex-start',
              gap: collapsed ? 0 : 10,
              padding: collapsed ? '12px 0' : '10px 20px',
              textDecoration: 'none',
              fontFamily: 'var(--font-mono)',
              fontSize: 12, fontWeight: isActive ? 600 : 400,
              letterSpacing: '0.1em',
              color: isActive ? 'var(--teal)' : 'var(--text-sec)',
              background: isActive ? 'var(--teal-dim)' : 'transparent',
              borderLeft: `2px solid ${isActive ? 'var(--teal)' : 'transparent'}`,
              transition: 'all 0.15s',
              overflow: 'hidden',
              whiteSpace: 'nowrap',
            })}
          >
            <div style={{
              width: 24, // Exatamente a mesma largura do wrapper da Logo
              display: 'flex',
              justifyContent: 'center', // Alinha perfeitamente ao centro da coluna
              flexShrink: 0
            }}>
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

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <div style={{
        padding: collapsed ? '14px 0' : '14px 20px',
        borderTop: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: collapsed ? 'center' : 'flex-start',
        gap: 6,
        transition: 'padding 0.25s ease',
      }}>
        {/* Usamos a mesma lógica de gap do Nav: 0 quando colapsado, 10 quando aberto */}
        <div style={{ display: 'flex', alignItems: 'center', gap: collapsed ? 0 : 10 }}>

          {/* Wrapper de 24px para centralizar a bolinha no mesmo eixo dos ícones */}
          <div style={{
            width: 24,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            flexShrink: 0
          }}>
            <span style={{
              width: 7, height: 7, borderRadius: '50%',
              background: 'var(--green)', display: 'inline-block',
              animation: 'pulse-dot 2s ease infinite', flexShrink: 0,
            }} />
          </div>

          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 11,
            color: 'var(--green)', letterSpacing: '0.1em',
            opacity: collapsed ? 0 : 1,
            width: collapsed ? 0 : 'auto',
            overflow: 'hidden',
            transition: 'opacity 0.2s ease, width 0.25s ease',
            whiteSpace: 'nowrap',
          }}>ONLINE</span>
        </div>

        {!collapsed && (
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)',
            marginLeft: 34 // 24px do wrapper + 10px do gap para alinhar com o texto de cima
          }}>{clock}</div>
        )}

        {!collapsed && p2Critical && (
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--red)', letterSpacing: '0.06em',
            marginLeft: 34 // Mantém o alerta alinhado com o texto
          }}>⚠ KPI P2 CRÍTICO</div>
        )}
      </div>
    </aside>
  );
}
