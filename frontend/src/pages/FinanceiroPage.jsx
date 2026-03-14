import { useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine, PieChart, Pie, Cell, LabelList,
} from 'recharts';
import { AlertTriangle, CheckCircle, TrendingUp } from 'lucide-react';
import {
  volumeMensal2025, produtos, violacoesReais2025,
} from '../data/mockData';

// ─── KPI card ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, meta, color, Icon, delay = 0 }) {
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
      {meta && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)' }}>{meta}</div>
      )}
    </div>
  );
}

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

// ─── Pie tooltip ──────────────────────────────────────────────────────────────
function PieTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 6, padding: '8px 12px',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-pri)', marginBottom: 4, fontWeight: 700 }}>{d?.id}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--red)' }}>violações: {d?.violacoes}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>taxa: {d?.taxaViolacao}%</div>
    </div>
  );
}

const PIE_COLORS = ['#E8002D', '#ff6d00', '#ffea00', '#00e676', '#60a5fa', '#a78bfa', '#f472b6', '#34d399', '#fb923c', '#f87171'];

export default function FinanceiroPage() {
  const [view, setView] = useState('geral'); // 'geral' | 'tecnico'

  const excessoP2 = violacoesReais2025.P2 - 39; // +3

  return (
    <main style={{
      flex: 1, padding: '20px 24px 40px',
      display: 'flex', flexDirection: 'column', gap: 16,
      maxWidth: 1600, width: '100%', margin: '0 auto',
    }}>

      {/* ── Header com disclaimer ─────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
        animation: 'fadeInUp 0.3s ease both',
      }}>
        <div>
          <h1 style={{
            fontFamily: 'var(--font-sans)', fontSize: 20, fontWeight: 700,
            color: 'var(--text-pri)', margin: 0, marginBottom: 6,
          }}>
            Impacto Estimado de Violações de OLA
          </h1>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
            color: 'var(--yellow)', background: 'rgba(255,234,0,0.08)',
            border: '1px solid rgba(255,234,0,0.3)',
            borderRadius: 4, padding: '3px 10px', letterSpacing: '0.08em',
          }}>
            ESTIMADO — baseado em penalidades SLA
          </span>
        </div>

        {/* Toggle */}
        <div style={{
          display: 'flex', background: 'var(--surface2)',
          border: '1px solid var(--border)', borderRadius: 6, padding: 2, gap: 2,
        }}>
          {['geral', 'tecnico'].map(v => (
            <button
              key={v}
              onClick={() => setView(v)}
              style={{
                fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
                padding: '5px 14px', borderRadius: 4, cursor: 'pointer',
                letterSpacing: '0.06em', transition: 'all 0.15s',
                background: view === v ? 'var(--surface3)' : 'transparent',
                color: view === v ? 'var(--text-pri)' : 'var(--text-sec)',
                border: view === v ? '1px solid var(--border-md)' : '1px solid transparent',
              }}
            >
              {v === 'geral' ? 'Geral' : 'Técnico'}
            </button>
          ))}
        </div>
      </div>

      {view === 'geral' && (
        <>
          {/* ── SEÇÃO 2: 3 KPI cards ──────────────────────────────────────── */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
            <KpiCard
              label="Violações P2 no ano"
              value={violacoesReais2025.P2}
              meta="meta: 36–39 · OLA 4h"
              color="var(--red)"
              Icon={AlertTriangle}
              delay={0}
            />
            <KpiCard
              label="Violações P3 no ano"
              value={violacoesReais2025.P3}
              meta="meta: 231–263 · OLA 12h"
              color="var(--green)"
              Icon={CheckCircle}
              delay={50}
            />
            <KpiCard
              label="Excesso P2 vs meta"
              value={`+${excessoP2} violações`}
              meta={`meta máxima: 39 · realizado: ${violacoesReais2025.P2}`}
              color="var(--orange)"
              Icon={TrendingUp}
              delay={100}
            />
          </div>

          {/* ── SEÇÃO 3: Violações por mês ───────────────────────────────── */}
          <ChartCard
            title="Violações de OLA por mês — 2025"
            sub="Linhas de referência = metas mensais P2 (3.25) e P3 (21.9)"
          >
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={volumeMensal2025} margin={{ top: 10, right: 16, bottom: 0, left: -10 }} barGap={4}>
                <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="mes"
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-muted)' }}
                  tickLine={false} axisLine={{ stroke: 'var(--border)' }}
                />
                <YAxis
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-muted)' }}
                  tickLine={false} axisLine={false}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    return (
                      <div style={{ background: 'var(--surface3)', border: '1px solid var(--border-md)', borderRadius: 6, padding: '8px 12px' }}>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
                        {payload.map((p, i) => (
                          <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: p.fill, marginBottom: 2 }}>
                            {p.name}: {p.value}
                          </div>
                        ))}
                      </div>
                    );
                  }}
                  cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                />
                <ReferenceLine y={3.25} stroke="var(--red)" strokeDasharray="4 4" strokeOpacity={0.6}
                  label={{ value: 'meta P2/mês', position: 'insideTopRight', fill: 'var(--red)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
                />
                <ReferenceLine y={21.9} stroke="var(--orange)" strokeDasharray="4 4" strokeOpacity={0.5}
                  label={{ value: 'meta P3/mês', position: 'insideTopRight', fill: 'var(--orange)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
                />
                <Bar dataKey="violP2" name="P2" fill="var(--red)"    fillOpacity={0.8} radius={[2,2,0,0]} />
                <Bar dataKey="violP3" name="P3" fill="var(--orange)" fillOpacity={0.8} radius={[2,2,0,0]} />
              </BarChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', gap: 16, marginTop: 8, justifyContent: 'flex-end' }}>
              {[['var(--red)', 'P2'], ['var(--orange)', 'P3']].map(([c, l]) => (
                <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: c, opacity: 0.8 }} />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>{l}</span>
                </div>
              ))}
            </div>
          </ChartCard>

          {/* ── SEÇÃO 4: Distribuição de violações por produto ────────────── */}
          <ChartCard
            title="Distribuição de violações por produto"
            sub="Total de violações OLA registradas em 2025 · passe o mouse para detalhes"
          >
            <div style={{ display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
              <ResponsiveContainer width={260} height={260} style={{ flexShrink: 0 }}>
                <PieChart>
                  <Pie
                    data={produtos}
                    dataKey="violacoes"
                    nameKey="id"
                    cx="50%" cy="50%"
                    innerRadius={60} outerRadius={110}
                    strokeWidth={1}
                    stroke="var(--bg)"
                  >
                    {produtos.map((p, i) => (
                      <Cell key={p.id} fill={PIE_COLORS[i % PIE_COLORS.length]} fillOpacity={0.85} />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                </PieChart>
              </ResponsiveContainer>

              {/* Legend */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {produtos.map((p, i) => (
                  <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{ width: 10, height: 10, borderRadius: 2, background: PIE_COLORS[i % PIE_COLORS.length], flexShrink: 0 }} />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)' }}>{p.id}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: 'var(--text-pri)' }}>{p.violacoes}</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>({p.taxaViolacao}%)</span>
                  </div>
                ))}
              </div>
            </div>
          </ChartCard>
        </>
      )}

      {view === 'tecnico' && (
        <>
          {/* ── Visão técnica: breakdown por produto × grupo ──────────────── */}
          <ChartCard
            title="Breakdown técnico — Violações por produto"
            sub="Detalhamento de taxa de violação · OLA P2 e P3 combinados"
          >
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={produtos}
                layout="vertical"
                margin={{ top: 4, right: 60, bottom: 4, left: 20 }}
                barSize={14}
              >
                <XAxis
                  type="number"
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
                  tickLine={false} axisLine={{ stroke: 'var(--border)' }}
                />
                <YAxis
                  type="category" dataKey="id" width={44}
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-sec)' }}
                  tickLine={false} axisLine={false}
                />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0]?.payload;
                    return (
                      <div style={{ background: 'var(--surface3)', border: '1px solid var(--border-md)', borderRadius: 6, padding: '8px 12px' }}>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: 'var(--text-pri)', marginBottom: 4 }}>{label}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#60a5fa' }}>total: {d?.total}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--red)' }}>violações: {d?.violacoes}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--orange)', fontWeight: 700 }}>taxa: {d?.taxaViolacao}%</div>
                      </div>
                    );
                  }}
                  cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                />
                <Bar dataKey="total"     name="Total"     fill="#60a5fa" fillOpacity={0.6} radius={[0,3,3,0]} />
                <Bar dataKey="violacoes" name="Violações"  fill="var(--red)" fillOpacity={0.85} radius={[0,3,3,0]}>
                  <LabelList
                    dataKey="taxaViolacao"
                    position="right"
                    formatter={v => `${v}%`}
                    style={{ fill: 'var(--text-sec)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* Tabela detalhada */}
          <div style={{
            background: 'var(--surface1)', border: '1px solid var(--border)',
            borderRadius: 8, overflow: 'hidden',
          }}>
            <div style={{ padding: '14px 20px 12px', borderBottom: '1px solid var(--border)' }}>
              <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>
                Tabela detalhada por produto
              </div>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--surface2)' }}>
                  {['Produto', 'Total incidentes', 'Violações', 'Taxa violação', 'Penalidade relativa'].map(h => (
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
                {[...produtos].sort((a, b) => b.taxaViolacao - a.taxaViolacao).map((p, i, arr) => (
                  <tr key={p.id} style={{
                    borderBottom: i < arr.length - 1 ? '1px solid var(--border)' : 'none',
                    background: p.taxaViolacao > 1.5 ? 'rgba(232,0,45,0.04)' : 'transparent',
                  }}>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: 'var(--text-pri)' }}>{p.id}</td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-sec)' }}>{p.total.toLocaleString('pt-BR')}</td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--red)', fontWeight: 700 }}>{p.violacoes}</td>
                    <td style={{ padding: '10px 16px', fontFamily: 'var(--font-mono)', fontSize: 12, color: p.taxaViolacao > 1.5 ? 'var(--red)' : 'var(--text-sec)' }}>
                      {p.taxaViolacao}%
                    </td>
                    <td style={{ padding: '10px 16px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{ width: 80, height: 4, background: 'var(--surface3)', borderRadius: 2, overflow: 'hidden' }}>
                          <div style={{
                            height: '100%',
                            width: `${Math.min(p.taxaViolacao / 2 * 100, 100)}%`,
                            background: p.taxaViolacao > 1.5 ? 'var(--red)' : p.taxaViolacao > 0.8 ? 'var(--orange)' : 'var(--green)',
                            borderRadius: 2,
                          }} />
                        </div>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                          {p.taxaViolacao > 1.5 ? 'alto' : p.taxaViolacao > 0.8 ? 'médio' : 'baixo'}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}
