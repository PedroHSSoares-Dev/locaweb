import {
  AreaChart, Area,
  LineChart, Line,
  XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { timeSeriesData, top3Servers } from '../data/mockData';

const SERIES_COLORS = [
  { stroke: '#E8002D', fill: 'rgba(232,0,45,0.12)' },
  { stroke: '#ff6d00', fill: 'rgba(255,109,0,0.10)' },
  { stroke: '#ffea00', fill: 'rgba(255,234,0,0.08)' },
];

const COMMON_GRID = (
  <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" vertical={false} />
);
const COMMON_XAXIS = (
  <XAxis
    dataKey="hour"
    tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
    tickLine={false}
    axisLine={{ stroke: 'var(--border)' }}
    interval={3}
  />
);
const COMMON_REFS = (
  <>
    <ReferenceLine y={80} stroke="rgba(232,0,45,0.3)" strokeDasharray="4 4"
      label={{ value: 'crítico', fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'rgba(232,0,45,0.5)', position: 'insideTopRight' }} />
    <ReferenceLine y={40} stroke="rgba(255,234,0,0.2)" strokeDasharray="4 4" />
  </>
);

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--surface3)',
      border: '1px solid var(--border-md)',
      borderRadius: 6, padding: '10px 14px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 10,
        color: 'var(--text-muted)', marginBottom: 8, letterSpacing: '0.08em',
      }}>
        {label}
      </div>
      {payload.map((entry, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', gap: 8,
          marginBottom: i < payload.length - 1 ? 4 : 0,
        }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: entry.color }} />
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)',
            maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {top3Servers.find(s => s.id === entry.dataKey)?.name || entry.dataKey}
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 12,
            fontWeight: 600, color: entry.color, marginLeft: 'auto',
          }}>
            {entry.value?.toFixed(1)}%
          </span>
        </div>
      ))}
    </div>
  );
}

function LegendItem({ server, color }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        width: 20, height: 2,
        background: `linear-gradient(90deg, ${color.stroke}44, ${color.stroke})`,
        borderRadius: 1,
      }} />
      <div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600, color: color.stroke }}>
          {server.name}
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>
          {server.failProb}% risco
        </div>
      </div>
    </div>
  );
}

export default function TimeSeriesChart({ viewMode }) {
  const serversToShow = viewMode === 'geral' ? [top3Servers[0]] : top3Servers;
  const colorsToShow  = viewMode === 'geral' ? [SERIES_COLORS[0]] : SERIES_COLORS;

  return (
    <div style={{
      background: 'var(--surface1)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '18px 20px',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
        marginBottom: 20,
      }}>
        <div>
          <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>
            Evolução da Probabilidade de Falha
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
            {viewMode === 'geral' ? 'Servidor mais crítico · 24h' : 'Top 3 servidores em risco · 24h'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 20 }}>
          {serversToShow.map((s, i) => (
            <LegendItem key={s.id} server={s} color={colorsToShow[i]} />
          ))}
        </div>
      </div>

      {/* ── Visão Geral: AreaChart (unchanged) ─────────────────────────────── */}
      {viewMode === 'geral' && (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={timeSeriesData} margin={{ top: 5, right: 4, bottom: 0, left: -8 }}>
            <defs>
              {serversToShow.map((s, i) => (
                <linearGradient key={s.id} id={`grad-${s.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor={colorsToShow[i].stroke} stopOpacity={0.25} />
                  <stop offset="95%" stopColor={colorsToShow[i].stroke} stopOpacity={0.01} />
                </linearGradient>
              ))}
            </defs>
            {COMMON_GRID}
            {COMMON_XAXIS}
            <YAxis
              domain={[70, 100]}
              tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
              tickLine={false} axisLine={false}
              tickFormatter={v => `${v}%`}
            />
            {COMMON_REFS}
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
            {serversToShow.map((s, i) => (
              <Area
                key={s.id} type="monotone" dataKey={s.id}
                stroke={colorsToShow[i].stroke} strokeWidth={1.5}
                fill={`url(#grad-${s.id})`} dot={false}
                activeDot={{ r: 3, fill: colorsToShow[i].stroke, stroke: 'var(--bg)', strokeWidth: 2 }}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      )}

      {/* ── Visão Técnica: LineChart, domain [40,100] ───────────────────────── */}
      {viewMode === 'tecnica' && (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={timeSeriesData} margin={{ top: 5, right: 4, bottom: 0, left: -8 }}>
            {COMMON_GRID}
            {COMMON_XAXIS}
            <YAxis
              domain={[40, 100]}
              tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
              tickLine={false} axisLine={false}
              tickFormatter={v => `${v}%`}
            />
            {COMMON_REFS}
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
            {serversToShow.map((s, i) => (
              <Line
                key={s.id} type="monotone" dataKey={s.id}
                stroke={colorsToShow[i].stroke} strokeWidth={2} dot={false}
                activeDot={{ r: 3, fill: colorsToShow[i].stroke, stroke: 'var(--bg)', strokeWidth: 2 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
