import { useState, useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from 'recharts';
import { AlertTriangle, Users, Package, Activity } from 'lucide-react';
import {
  previsaoVolume, volumeDiario30d, heatmapData, riscoOlaPorProduto,
} from '../data/mockData';
import DrillDownPanel from '../components/DrillDownPanel';

// ─── KPI Card ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, color, Icon, delay = 0 }) {
  return (
    <div style={{
      background: 'var(--surface1)',
      border: `1px solid ${color}33`,
      borderTop: `2px solid ${color}`,
      borderRadius: 8, padding: '18px 22px',
      display: 'flex', flexDirection: 'column', gap: 10,
      animation: `fadeInUp 0.4s ease ${delay}ms both`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 500,
          color: 'var(--text-sec)', textTransform: 'uppercase', letterSpacing: '0.07em',
        }}>{label}</span>
        <span style={{
          width: 34, height: 34, borderRadius: 8, display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          background: `${color}18`, color,
        }}>
          <Icon size={16} strokeWidth={1.8} />
        </span>
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700,
        color, lineHeight: 1, letterSpacing: '-0.02em',
      }}>{value}</div>
      {sub && (
        <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)' }}>{sub}</div>
      )}
    </div>
  );
}

// ─── Chart card ───────────────────────────────────────────────────────────────
function ChartCard({ children, title, sub }) {
  return (
    <div style={{
      background: 'var(--surface1)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '18px 20px',
    }}>
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>{title}</div>
        {sub && <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)', marginTop: 3 }}>{sub}</div>}
      </div>
      {children}
    </div>
  );
}

// ─── Heatmap SVG custom ───────────────────────────────────────────────────────
function Heatmap() {
  const maxVal = useMemo(() => {
    let m = 0;
    heatmapData.forEach(row => row.horas.forEach(v => { if (v > m) m = v; }));
    return m;
  }, []);

  const cellW = 28;
  const cellH = 28;
  const labelW = 36;
  const hours = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23];
  const showHours = [0, 6, 12, 18, 23];

  function cellColor(v) {
    const pct = v / maxVal;
    if (pct < 0.15) return `rgba(255,255,255,0.04)`;
    if (pct < 0.35) return `rgba(255,109,0,${0.2 + pct * 0.4})`;
    if (pct < 0.65) return `rgba(255,109,0,${0.5 + pct * 0.3})`;
    return `rgba(232,0,45,${0.5 + pct * 0.5})`;
  }

  const svgW = labelW + hours.length * cellW + 8;
  const svgH = heatmapData.length * cellH + 28;

  return (
    <svg width="100%" viewBox={`0 0 ${svgW} ${svgH}`} style={{ overflow: 'visible' }}>
      {/* Hour labels */}
      {hours.map(h => showHours.includes(h) && (
        <text
          key={h}
          x={labelW + h * cellW + cellW / 2}
          y={14}
          textAnchor="middle"
          style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
        >
          {h}h
        </text>
      ))}

      {/* Rows */}
      {heatmapData.map((row, ri) => (
        <g key={row.dia}>
          {/* Day label */}
          <text
            x={labelW - 6}
            y={28 + ri * cellH + cellH / 2 + 4}
            textAnchor="end"
            style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-sec)' }}
          >
            {row.dia}
          </text>
          {/* Cells */}
          {row.horas.map((v, hi) => (
            <g key={hi}>
              <rect
                x={labelW + hi * cellW + 1}
                y={28 + ri * cellH + 1}
                width={cellW - 2}
                height={cellH - 2}
                rx={3}
                fill={cellColor(v)}
              />
              <title>{`${row.dia} ${hi}h: ${v} incidentes`}</title>
            </g>
          ))}
        </g>
      ))}
    </svg>
  );
}

// ─── Severity badge ───────────────────────────────────────────────────────────
function StatusBadge({ prob }) {
  const [color, label] =
    prob > 30 ? ['var(--red)', 'ALTO RISCO'] :
    prob > 15 ? ['var(--yellow)', 'ATENÇÃO']  :
                ['var(--green)', 'NORMAL'];
  return (
    <span style={{
      fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
      color, background: `${color}18`, border: `1px solid ${color}44`,
      borderRadius: 3, padding: '2px 8px', letterSpacing: '0.08em',
    }}>{label}</span>
  );
}

export default function MonitoramentoPage() {
  const [panelItem, setPanelItem] = useState(null);

  // Combine 30d history + 7d forecast
  const volumeComPrevisao = useMemo(() => {
    const hist = volumeDiario30d.map(d => ({ ...d, tipo: 'historico' }));
    const prev = [
      { dia: 'D+1', P2: 14, P3: 38, tipo: 'previsao' },
      { dia: 'D+2', P2: 13, P3: 41, tipo: 'previsao' },
      { dia: 'D+3', P2: 15, P3: 36, tipo: 'previsao' },
      { dia: 'D+4', P2: 11, P3: 32, tipo: 'previsao' },
      { dia: 'D+5', P2: 16, P3: 44, tipo: 'previsao' },
      { dia: 'D+6', P2: 8,  P3: 18, tipo: 'previsao' },
      { dia: 'D+7', P2: 7,  P3: 14, tipo: 'previsao' },
    ];
    return [...hist, ...prev];
  }, []);

  const dividerIndex = volumeDiario30d.length - 1; // last historical index

  return (
    <main style={{
      flex: 1, padding: '20px 24px 40px',
      display: 'flex', flexDirection: 'column', gap: 16,
      maxWidth: 1600, width: '100%', margin: '0 auto',
    }}>

      {/* ── SEÇÃO 1: KPI Cards ────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <KpiCard
          label="Incidentes hoje (D+1)"
          value={previsaoVolume.D1.total}
          sub="previsão Prophet"
          color="var(--orange)"
          Icon={Activity}
          delay={0}
        />
        <KpiCard
          label="P2 em aberto estimado"
          value={previsaoVolume.D1.P2}
          sub="Alta prioridade · OLA 4h"
          color="var(--red)"
          Icon={AlertTriangle}
          delay={50}
        />
        <KpiCard
          label="P3 em aberto estimado"
          value={previsaoVolume.D1.P3}
          sub="Média prioridade · OLA 12h"
          color="var(--yellow)"
          Icon={Package}
          delay={100}
        />
        <KpiCard
          label="Grupo mais crítico"
          value="Team07"
          sub="8.94% taxa de violação"
          color="var(--red)"
          Icon={Users}
          delay={150}
        />
      </div>

      {/* ── SEÇÃO 2: Volume diário + previsão ────────────────────────────── */}
      <ChartCard
        title="Volume de incidentes — 30 dias + previsão D+7"
        sub="Histórico real (dez/2025) + previsão Prophet · linha tracejada = previsão"
      >
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={volumeComPrevisao} margin={{ top: 8, right: 16, bottom: 0, left: -10 }}>
            <defs>
              <linearGradient id="gradP2" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#E8002D" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#E8002D" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="gradP3" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#ff6d00" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#ff6d00" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="dia"
              tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
              tickLine={false} axisLine={{ stroke: 'var(--border)' }}
              interval={4}
            />
            <YAxis
              tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
              tickLine={false} axisLine={false}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const isPrev = payload[0]?.payload?.tipo === 'previsao';
                return (
                  <div style={{
                    background: 'var(--surface3)', border: '1px solid var(--border-md)',
                    borderRadius: 6, padding: '8px 12px',
                  }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>
                      {label} {isPrev && '· previsão'}
                    </div>
                    {payload.map((p, i) => (
                      <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: p.stroke || p.fill, marginBottom: 2 }}>
                        {p.name}: {p.value}
                      </div>
                    ))}
                  </div>
                );
              }}
              cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }}
            />
            <ReferenceLine
              x={volumeDiario30d[volumeDiario30d.length - 1].dia}
              stroke="rgba(255,255,255,0.2)"
              strokeDasharray="6 3"
              label={{ value: '← Histórico · Previsão →', position: 'insideTopLeft', fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
            />
            <Area type="monotone" dataKey="P2" name="P2" stroke="var(--red)"    strokeWidth={2} fill="url(#gradP2)" dot={false} />
            <Area type="monotone" dataKey="P3" name="P3" stroke="var(--orange)" strokeWidth={2} fill="url(#gradP3)" dot={false} />
          </AreaChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', gap: 16, marginTop: 8, justifyContent: 'flex-end' }}>
          {[['var(--red)', 'P2'], ['var(--orange)', 'P3']].map(([c, l]) => (
            <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: c }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>{l}</span>
            </div>
          ))}
        </div>
      </ChartCard>

      {/* ── SEÇÃO 3: Heatmap sazonalidade ─────────────────────────────────── */}
      <ChartCard
        title="Sazonalidade de incidentes KPI"
        sub="Concentração por hora × dia da semana · período 2023–2025 · pico: Qui 11h (391)"
      >
        <div style={{ overflowX: 'auto' }}>
          <div style={{ minWidth: 700 }}>
            <Heatmap />
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>baixo</span>
          {['rgba(255,255,255,0.04)', 'rgba(255,109,0,0.3)', 'rgba(255,109,0,0.7)', 'rgba(232,0,45,0.7)', 'rgba(232,0,45,0.95)'].map((c, i) => (
            <div key={i} style={{ width: 24, height: 12, borderRadius: 2, background: c }} />
          ))}
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>alto</span>
        </div>
      </ChartCard>

      {/* ── SEÇÃO 4: Tabela de alertas por produto ────────────────────────── */}
      <div style={{
        background: 'var(--surface1)', border: '1px solid var(--border)',
        borderRadius: 8, overflow: 'hidden',
      }}>
        <div style={{
          padding: '14px 20px 12px',
          borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>
              Alertas por produto — Risco de violação de OLA
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)', marginTop: 3 }}>
              XGBoost simulado · atualizar com outputs/risco_ola.json
            </div>
          </div>
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: 'var(--surface2)' }}>
              {['Produto', 'Incidentes pendentes', 'Probabilidade violação OLA', 'Status', ''].map(h => (
                <th key={h} style={{
                  padding: '8px 16px', textAlign: 'left',
                  fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                  color: 'var(--text-muted)', letterSpacing: '0.1em',
                  borderBottom: '1px solid var(--border)',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {riscoOlaPorProduto.map((r, i) => (
              <tr
                key={r.produto}
                style={{
                  background: r.probViolacao > 30 ? 'rgba(232,0,45,0.05)' : r.probViolacao > 15 ? 'rgba(255,234,0,0.04)' : 'transparent',
                  borderBottom: i < riscoOlaPorProduto.length - 1 ? '1px solid var(--border)' : 'none',
                }}
              >
                <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: 'var(--text-pri)' }}>
                  {r.produto}
                </td>
                <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-sec)' }}>
                  {r.incidentesPendentes}
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{
                      width: 80, height: 4, background: 'var(--surface3)', borderRadius: 2, overflow: 'hidden',
                    }}>
                      <div style={{
                        height: '100%',
                        width: `${r.probViolacao}%`,
                        background: r.probViolacao > 30 ? 'var(--red)' : r.probViolacao > 15 ? 'var(--yellow)' : 'var(--green)',
                        borderRadius: 2,
                      }} />
                    </div>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-pri)', fontWeight: 700 }}>
                      {r.probViolacao}%
                    </span>
                  </div>
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <StatusBadge prob={r.probViolacao} />
                </td>
                <td style={{ padding: '10px 16px' }}>
                  <button
                    onClick={() => setPanelItem(r)}
                    style={{
                      fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
                      color: 'var(--text-sec)', border: '1px solid var(--border)',
                      background: 'var(--surface2)', borderRadius: 4,
                      padding: '4px 10px', cursor: 'pointer', letterSpacing: '0.06em',
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-pri)'; e.currentTarget.style.borderColor = 'var(--border-md)'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-sec)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
                  >
                    Detalhes
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Drill-down panel */}
      {panelItem && (
        <DrillDownPanel item={panelItem} onClose={() => setPanelItem(null)} />
      )}
    </main>
  );
}
