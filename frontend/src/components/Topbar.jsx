import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { BarChart2, Activity, Terminal } from 'lucide-react';
import { violacoesReais2025, olaTargets } from '../data/mockData';

const TABS = [
  { to: '/gestao',        label: 'Gestão',       Icon: BarChart2 },
  { to: '/monitoramento', label: 'Monitoramento', Icon: Activity  },
  { to: '/tecnico',       label: 'Técnico',       Icon: Terminal  },
];

export default function Topbar() {
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const tick = () => {
      setTimeStr(new Date().toLocaleTimeString('pt-BR', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      }));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const p2Critical = violacoesReais2025.P2 > olaTargets.P2.metaViolacoesAno.max;
  const p3Critical = violacoesReais2025.P3 > olaTargets.P3.metaViolacoesAno.max;
  const allOk = !p2Critical && !p3Critical;

  return (
    <header style={{
      position: 'sticky', top: 0, zIndex: 100,
      background: 'rgba(10,10,10,0.97)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border-md)',
      display: 'flex', alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px', height: 56, gap: 16,
    }}>

      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontWeight: 700,
          fontSize: 18, color: 'var(--red)', letterSpacing: '-0.02em',
        }}>locaweb</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: 'var(--text-muted)', letterSpacing: '0.15em',
          padding: '2px 7px', border: '1px solid var(--border-md)',
          borderRadius: 3, background: 'var(--surface3)',
        }}>INFRA PREDICT</span>
      </div>

      {/* Nav tabs */}
      <nav style={{
        display: 'flex', alignItems: 'stretch',
        height: 56, gap: 2, flex: 1, justifyContent: 'center',
      }}>
        {TABS.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => isActive ? 'tab tab-active' : 'tab'}
          >
            <Icon size={13} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Status badge + timestamp */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexShrink: 0 }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          letterSpacing: '0.1em', padding: '3px 9px', borderRadius: 4,
          background: allOk ? 'rgba(0,230,118,0.10)' : 'var(--red-dim)',
          color: allOk ? 'var(--green)' : 'var(--red)',
          border: `1px solid ${allOk ? 'var(--green)' : 'var(--red)'}`,
        }}>
          {allOk ? '● KPI DENTRO DA META' : '● KPI P2 CRÍTICO'}
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-muted)', borderLeft: '1px solid var(--border)', paddingLeft: 14,
        }}>
          <span style={{ color: 'var(--text-sec)' }}>live </span>
          <span style={{ color: 'var(--text-pri)' }}>{timeStr}</span>
        </span>
      </div>
    </header>
  );
}
