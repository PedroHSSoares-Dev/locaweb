import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { violacoesReais2025, olaTargets } from '../data/mockData';

const NAV = [
  { to: '/gestao',        label: 'GESTÃO',         icon: '▣' },
  { to: '/monitoramento', label: 'MONITORAMENTO',   icon: '◈' },
  { to: '/tecnico',       label: 'TÉCNICO',         icon: '▦' },
];

export default function Sidebar() {
  const [clock, setClock] = useState('');

  useEffect(() => {
    const tick = () =>
      setClock(new Date().toLocaleTimeString('pt-BR', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const p2Critical = violacoesReais2025.P2 > olaTargets.P2.metaViolacoesAno.max;

  return (
    <aside style={{
      width: 220,
      height: '100vh',
      background: 'var(--surface1)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      flexShrink: 0,
      position: 'fixed',
      top: 0, left: 0,
      zIndex: 100,
    }}>

      {/* ── Logo ──────────────────────────────────────────────────────────── */}
      <div style={{
        padding: '20px 20px 18px',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700,
          color: 'var(--teal)', letterSpacing: '0.1em',
        }}>PREDICTFY</div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-sec)', letterSpacing: '0.08em', marginTop: 3,
        }}>AIOPS // LOCAWEB</div>
      </div>

      {/* ── Nav ───────────────────────────────────────────────────────────── */}
      <nav style={{ flex: 1, padding: '10px 0' }}>
        {NAV.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '10px 20px',
              textDecoration: 'none',
              fontFamily: 'var(--font-mono)',
              fontSize: 12, fontWeight: isActive ? 600 : 400,
              letterSpacing: '0.1em',
              color: isActive ? 'var(--teal)' : 'var(--text-sec)',
              background: isActive ? 'var(--teal-dim)' : 'transparent',
              borderLeft: `2px solid ${isActive ? 'var(--teal)' : 'transparent'}`,
              transition: 'all 0.15s',
            })}
          >
            <span style={{ fontSize: 12, opacity: 0.8 }}>{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <div style={{
        padding: '14px 20px',
        borderTop: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', gap: 6,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: 'var(--green)', display: 'inline-block',
            animation: 'pulse-dot 2s ease infinite',
          }} />
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 11,
            color: 'var(--green)', letterSpacing: '0.1em',
          }}>ONLINE</span>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)',
        }}>{clock}</div>
        {p2Critical && (
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--red)', letterSpacing: '0.06em',
          }}>⚠ KPI P2 CRÍTICO</div>
        )}
      </div>
    </aside>
  );
}
