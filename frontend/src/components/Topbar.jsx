import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { BarChart2, LayoutGrid, Terminal, TrendingUp } from 'lucide-react';
import { servers, horizonMultiplier } from '../data/mockData';
import { useDashboard } from '../context/DashboardContext';

const HORIZONS = ['30min', '1h', '6h', '12h', '24h'];

const TABS = [
  { to: '/gestao',        label: 'Gestão',            Icon: BarChart2  },
  { to: '/monitoramento', label: 'Monitoramento',      Icon: LayoutGrid },
  { to: '/tecnico',       label: 'Técnico',            Icon: Terminal   },
  { to: '/financeiro',    label: 'Impacto Financeiro', Icon: TrendingUp },
];

function GlobalStatusBadge() {
  const maxProb = Math.max(...servers.map(s => s.failProb));
  const color = maxProb >= 80 ? 'var(--red)' : maxProb >= 40 ? 'var(--orange)' : 'var(--green)';
  const label = maxProb >= 80 ? 'CRÍTICO' : maxProb >= 40 ? 'ALERTA' : 'NORMAL';

  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 10px', borderRadius: 4,
      background: `${color}18`,
      border: `1px solid ${color}44`,
      fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
      color, letterSpacing: '0.08em',
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%',
        background: color,
        boxShadow: `0 0 6px ${color}`,
        animation: maxProb >= 40 ? 'pulse-glow 2s ease-in-out infinite' : 'none',
      }} />
      SISTEMA {label}
    </span>
  );
}

export default function Topbar() {
  const { horizon, setHorizon } = useDashboard();
  const [tick, setTick] = useState(0);
  const location = useLocation();

  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const now = new Date();
  const timeStr = now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  // Badge: servers at risk adjusted by current horizon
  const mult = horizonMultiplier[horizon]?.prob ?? 1.0;
  const atRiskCount = servers.filter(s => s.failProb * mult >= 40).length;

  return (
    <header style={{
      position: 'sticky', top: 0, zIndex: 100,
      background: 'rgba(10,10,10,0.95)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border)',
      padding: '0 24px',
      height: 56,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      gap: 24,
    }}>

      {/* Left: logo + nav tabs */}
      <div style={{ display: 'flex', alignItems: 'center', flexShrink: 0, height: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginRight: 24 }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontWeight: 700,
            fontSize: 18, color: 'var(--red)',
            letterSpacing: '-0.02em',
          }}>
            locaweb
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600,
            color: 'var(--text-muted)', letterSpacing: '0.15em',
            padding: '2px 7px', border: '1px solid var(--border-md)',
            borderRadius: 3,
          }}>
            INFRA PREDICT
          </span>
        </div>

        <div style={{ width: 1, height: 20, background: 'var(--border-md)', marginRight: 20 }} />

        <nav style={{ display: 'flex', alignItems: 'stretch', height: '100%', gap: 2 }}>
          {TABS.map(({ to, label, Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => isActive ? 'tab tab-active' : 'tab'}
            >
              <Icon size={13} />
              {label}
              {to === '/tecnico' && atRiskCount > 0 && (
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                  color: '#fff', background: 'var(--red)',
                  borderRadius: 10, padding: '1px 5px',
                  lineHeight: 1.4, marginLeft: 2,
                }}>
                  {atRiskCount}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Center: horizon selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 10,
          color: 'var(--text-muted)', letterSpacing: '0.1em',
          marginRight: 4,
        }}>
          HORIZONTE
        </span>
        <div style={{
          display: 'flex', gap: 2,
          background: 'var(--surface2)', borderRadius: 6,
          padding: 2, border: '1px solid var(--border)',
        }}>
          {HORIZONS.map(h => (
            <button
              key={h}
              onClick={() => setHorizon(h)}
              style={{
                padding: '3px 10px', borderRadius: 4,
                fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 500,
                transition: 'all 0.15s ease',
                background: horizon === h ? 'var(--red)' : 'transparent',
                color: horizon === h ? '#fff' : 'var(--text-sec)',
                letterSpacing: '0.04em',
              }}
            >
              {h}
            </button>
          ))}
        </div>
      </div>

      {/* Right: status + timestamp */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0 }}>
        <GlobalStatusBadge />
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-muted)',
          borderLeft: '1px solid var(--border)', paddingLeft: 16,
        }}>
          <span style={{ color: 'var(--text-sec)' }}>atualizado </span>
          <span style={{ color: 'var(--text-pri)' }}>{timeStr}</span>
        </div>
      </div>
    </header>
  );
}
