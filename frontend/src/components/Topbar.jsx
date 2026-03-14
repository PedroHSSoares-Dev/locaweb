import { useEffect, useState } from 'react';
import { LayoutGrid, TrendingUp } from 'lucide-react';
import { servers } from '../data/mockData';

const HORIZONS = ['30min', '1h', '6h', '12h', '24h'];

const atRiskCount = servers.filter(s => s.failProb >= 40).length;

function GlobalStatusBadge() {
  const maxProb = Math.max(...servers.map(s => s.failProb));
  const color = maxProb >= 80 ? 'var(--red)' : maxProb >= 40 ? 'var(--orange)' : 'var(--green)';
  const label = maxProb >= 80 ? 'CRÍTICO' : maxProb >= 40 ? 'ALERTA' : 'NORMAL';

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
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
    </div>
  );
}

export default function Topbar({
  horizon, setHorizon,
  viewMode, setViewMode,
  activePage, onNavigate,
}) {
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const now = new Date();
  const timeStr = now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  const NAV_TABS = [
    { id: 'dashboard', label: 'Monitoramento', Icon: LayoutGrid },
    { id: 'financial', label: 'Impacto Financeiro', Icon: TrendingUp },
  ];

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
      <div style={{ display: 'flex', alignItems: 'center', gap: 0, flexShrink: 0, height: '100%' }}>
        {/* Logo */}
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

        {/* Separator */}
        <div style={{
          width: 1, height: 20,
          background: 'var(--border-md)',
          marginRight: 20,
        }} />

        {/* Nav tabs */}
        <nav style={{ display: 'flex', alignItems: 'stretch', height: '100%', gap: 2 }}>
          {NAV_TABS.map(({ id, label, Icon }) => {
            const isActive = activePage === id;
            const showBadge = id === 'financial' && viewMode === 'tecnica';
            return (
              <button
                key={id}
                onClick={() => onNavigate(id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 7,
                  padding: '0 14px',
                  height: '100%',
                  fontFamily: 'var(--font-sans)', fontSize: 12, fontWeight: 500,
                  color: isActive ? 'var(--text-pri)' : 'var(--text-sec)',
                  background: 'transparent',
                  borderBottom: isActive ? '2px solid var(--red)' : '2px solid transparent',
                  transition: 'color 0.15s ease, border-color 0.15s ease',
                  position: 'relative',
                }}
                onMouseEnter={e => {
                  if (!isActive) e.currentTarget.style.color = 'var(--text-pri)';
                }}
                onMouseLeave={e => {
                  if (!isActive) e.currentTarget.style.color = 'var(--text-sec)';
                }}
              >
                <Icon size={13} strokeWidth={isActive ? 2.2 : 1.8} />
                {label}
                {showBadge && (
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                    color: '#fff',
                    background: 'var(--red)',
                    borderRadius: 10,
                    padding: '1px 5px',
                    lineHeight: 1.4,
                    marginLeft: 2,
                  }}>
                    {atRiskCount}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Center: controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        {/* Horizon selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--text-muted)', letterSpacing: '0.1em',
            marginRight: 6,
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

        {/* View toggle */}
        <div style={{
          display: 'flex', gap: 2,
          background: 'var(--surface2)', borderRadius: 6,
          padding: 2, border: '1px solid var(--border)',
        }}>
          {['geral', 'tecnica'].map(mode => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              style={{
                padding: '3px 12px', borderRadius: 4,
                fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 500,
                transition: 'all 0.15s ease',
                background: viewMode === mode ? 'var(--surface3)' : 'transparent',
                color: viewMode === mode ? 'var(--text-pri)' : 'var(--text-sec)',
                border: viewMode === mode ? '1px solid var(--border-md)' : '1px solid transparent',
              }}
            >
              {mode === 'geral' ? 'Visão Geral' : 'Visão Técnica'}
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
