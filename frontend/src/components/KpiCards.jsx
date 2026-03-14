import { getKpis, serverDeltas, servers } from '../data/mockData';
import { Server, AlertTriangle, ShieldAlert, Clock } from 'lucide-react';

function Delta({ value, unit = '' }) {
  if (value === undefined) return null;
  const positive = value >= 0;
  const color = positive ? 'var(--red)' : 'var(--green)';
  return (
    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color, marginLeft: 6 }}>
      {positive ? '▲' : '▼'} {Math.abs(value).toFixed(1)}{unit}
    </span>
  );
}

// FIX-07: range textual instead of raw hours
function formatIncidente(horas) {
  if (horas < 1) return 'menos de 1h';
  if (horas < 3) return '1h – 3h';
  if (horas < 6) return '3h – 6h';
  return 'mais de 6h';
}

function Card({ icon: Icon, label, value, unit, sub, accent, delta, deltaUnit, style = {} }) {
  return (
    <div style={{
      background: 'var(--surface1)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '18px 22px',
      display: 'flex', flexDirection: 'column', gap: 10,
      position: 'relative', overflow: 'hidden',
      animation: 'fadeInUp 0.4s ease both',
      transition: 'border-color 0.2s',
      ...style,
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--border-md)'}
      onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
    >
      {/* top accent strip */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        background: accent, opacity: 0.6,
      }} />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 500,
          color: 'var(--text-sec)', letterSpacing: '0.06em', textTransform: 'uppercase',
        }}>
          {label}
        </span>
        <span style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: 28, height: 28, borderRadius: 6,
          background: `${accent}18`, color: accent,
        }}>
          <Icon size={14} strokeWidth={2} />
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 600,
          color: 'var(--text-pri)', lineHeight: 1,
        }}>
          {value}
        </span>
        {unit && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--text-sec)' }}>
            {unit}
          </span>
        )}
        {delta !== undefined && <Delta value={delta} unit={deltaUnit} />}
      </div>

      {sub && (
        <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-muted)' }}>
          {sub}
        </div>
      )}
    </div>
  );
}

export default function KpiCards({ horizon, viewMode }) {
  const kpis = getKpis(horizon);

  // FIX-03: "Servidores Críticos" replaces "Probabilidade Média"
  const criticos = servers.filter(sv => sv.failProb >= 75).length;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
      <Card
        icon={AlertTriangle}
        label="Alertas Ativos"
        value={kpis.activeAlerts}
        accent="var(--orange)"
        sub={`failProb ≥ 40% — ${horizon}`}
        style={{ animationDelay: '0ms' }}
      />
      <Card
        icon={Clock}
        label="Próximo Incidente"
        value={formatIncidente(kpis.nextIncident)}
        accent="var(--red)"
        sub={`baseado no horizonte ${horizon}`}
        style={{
          animationDelay: '60ms',
          border: '1px solid rgba(232,0,45,0.2)',
        }}
      />
      <Card
        icon={ShieldAlert}
        label="Servidores Críticos"
        value={`${criticos} / ${servers.length}`}
        accent="var(--yellow)"
        sub={viewMode === 'tecnica' ? '↑ +1 vs. 1h atrás' : `failProb ≥ 75% — agora`}
        style={{ animationDelay: '120ms' }}
      />
      <Card
        icon={Server}
        label="Servidores Monitorados"
        value={kpis.total}
        accent="var(--text-sec)"
        sub={`${kpis.total} instâncias ativas`}
        style={{ animationDelay: '180ms' }}
      />
    </div>
  );
}
