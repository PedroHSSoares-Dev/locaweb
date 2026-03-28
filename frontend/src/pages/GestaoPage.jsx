import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, PieChart, Pie, Cell,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle } from 'lucide-react';
import {
  volumeMensal2025, produtos, kpiAtingimento,
  violacoesReais2025, olaTargets,
} from '../data/mockData';
import { useApi } from '../hooks/useApi';
import SemDados from '../components/SemDados';
import PeriodoToggle from '../components/PeriodoToggle';

// ─── Skeleton ─────────────────────────────────────────────────────────────────
function Skeleton({ height = 80 }) {
  return <div className="skeleton" style={{ height }} />;
}

// ─── Page header ──────────────────────────────────────────────────────────────
function PageHeader({ title, sub, rightSlot }) {
  return (
    <div style={{
      padding: '16px 28px',
      borderBottom: '1px solid var(--border)',
      background: 'var(--surface1)',
      marginBottom: 0,
      flexShrink: 0,
      position: 'sticky',
      top: 0,
      zIndex: 10,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
    }}>
      <div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 600,
          color: 'var(--text-pri)', letterSpacing: '0.08em', textTransform: 'uppercase',
        }}>{title}</div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-sec)', marginTop: 3, letterSpacing: '0.08em',
        }}>{sub}</div>
      </div>
      {rightSlot && <div>{rightSlot}</div>}
    </div>
  );
}

// ─── Module card ──────────────────────────────────────────────────────────────
function Module({ n, title, sub, action, children, noPad = false }) {
  return (
    <div style={{
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 6, overflow: 'hidden',
    }}>
      <div style={{
        padding: '10px 16px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
      }}>
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)',
            letterSpacing: '0.16em', marginBottom: 3,
          }}>MODULE {String(n).padStart(2, '0')}</div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600,
            color: 'var(--text-pri)', textTransform: 'uppercase', letterSpacing: '0.04em',
          }}>{title}</div>
          {sub && (
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 11,
              color: 'var(--text-sec)', marginTop: 3,
            }}>{sub}</div>
          )}
        </div>
        {action}
      </div>
      <div style={noPad ? {} : { padding: '20px 24px 24px' }}>{children}</div>
    </div>
  );
}

// ─── KPI card ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, color, delay = 0 }) {
  return (
    <div style={{
      background: 'var(--surface3)',
      border: '1px solid var(--border)',
      borderTop: `2px solid ${color}`,
      borderRadius: 6, padding: '20px 24px',
      minHeight: 120,
      display: 'flex', flexDirection: 'column', gap: 8,
      animation: `fadeInUp 0.4s ease ${delay}ms both`,
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
        color: 'var(--text-sec)', textTransform: 'uppercase', letterSpacing: '0.14em',
      }}>{label}</div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 400,
        color: 'var(--text-pri)', lineHeight: 1,
      }}>{value}</div>
      {sub && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-sec)', letterSpacing: '0.04em',
        }}>{sub}</div>
      )}
    </div>
  );
}

// ─── Status banner (P2 / P3) ──────────────────────────────────────────────────
function StatusBanner({ priority, violations, metaMin, metaMax, ola }) {
  const ok = violations <= metaMax;
  const color = ok ? 'var(--green)' : 'var(--red)';
  const dimBg = ok ? 'var(--green-dim)' : 'var(--red-dim)';
  return (
    <div style={{
      background: dimBg, border: `1px solid ${color}`,
      borderRadius: 6, padding: '18px 22px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      animation: 'fadeInUp 0.3s ease both',
    }}>
      <div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
          color: 'var(--text-sec)', letterSpacing: '0.12em',
          textTransform: 'uppercase', marginBottom: 6,
        }}>KPI {priority} · OLA {ola}</div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 36, fontWeight: 400,
          color, lineHeight: 1,
        }}>{violations} <span style={{ fontSize: 14, opacity: 0.7 }}>violações</span></div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-sec)', marginTop: 6,
        }}>META: {metaMin}–{metaMax} · ANO 2025</div>
      </div>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
        color, background: dimBg, border: `1px solid ${color}`,
        borderRadius: 3, padding: '4px 10px', letterSpacing: '0.1em',
      }}>{ok ? 'DENTRO DA META' : 'ACIMA DA META'}</span>
    </div>
  );
}

// ─── Chart tooltip ────────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 4, padding: '8px 12px',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)', marginBottom: 6 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: p.color || p.fill, marginBottom: 2 }}>
          {p.name}: {p.value}
        </div>
      ))}
    </div>
  );
}

// ─── Gauge donut ──────────────────────────────────────────────────────────────
function Gauge({ label, pct, color, sub }) {
  const capped = Math.min(pct, 100);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
      <div style={{ position: 'relative', width: 160, height: 160 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={[{ value: capped }, { value: 100 - capped }]}
              cx="50%" cy="50%"
              innerRadius={52} outerRadius={72}
              startAngle={90} endAngle={-270}
              dataKey="value" strokeWidth={0}
            >
              <Cell fill={color} fillOpacity={0.9} />
              <Cell fill="var(--surface4)" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 26, fontWeight: 400,
            color, lineHeight: 1,
          }}>{pct}%</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>
            ATINGIMENTO
          </div>
        </div>
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600,
        color: 'var(--text-pri)', letterSpacing: '0.06em', textTransform: 'uppercase',
      }}>{label}</div>
      {sub && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)', textAlign: 'center' }}>{sub}</div>
      )}
    </div>
  );
}

// ─── Legend row ───────────────────────────────────────────────────────────────
function Legend({ items }) {
  return (
    <div style={{ display: 'flex', gap: 16, marginTop: 8, justifyContent: 'flex-end' }}>
      {items.map(([c, l]) => (
        <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <div style={{ width: 8, height: 8, borderRadius: 2, background: c, opacity: 0.85 }} />
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)' }}>{l}</span>
        </div>
      ))}
    </div>
  );
}

// ─── Filtro de período ────────────────────────────────────────────────────────
const PERIODO_LABELS = {
  'MÊS':       'Dez/2025',
  'TRIMESTRE': 'Q4 2025 · Out–Dez',
  'ANO':       'Jan–Dez 2025',
};

function filtrarPorPeriodo(dados, periodo) {
  if (periodo === 'MÊS')       return dados.slice(11, 12);
  if (periodo === 'TRIMESTRE') return dados.slice(9, 12);
  return dados;
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function GestaoPage() {
  const navigate = useNavigate();
  const [periodo, setPeriodo] = useState('ANO');

  // ── Dados de modelo via API ────────────────────────────────────────────────
  const { data: d1Data, loading: d1Loading, disponivel: d1Disponivel } = useApi('/previsoes/d1');
  const { data: d7Data,                     disponivel: d7Disponivel } = useApi('/previsoes/d7');
  const PERIODO_API = { 'MÊS': 'mes', 'TRIMESTRE': 'trimestre', 'ANO': 'ano' };
  const { data: kpiData, loading: kpiLoading, disponivel: kpiDisponivel } = useApi('/kpi', {
    periodo: PERIODO_API[periodo] ?? 'ano',
  });

  const prevLoading    = d1Loading;
  const prevDisponivel = d1Disponivel;

  // Fallback para mockData enquanto kpi_atingimento.json não existe
  const p2 = kpiDisponivel ? kpiData.P2 : kpiAtingimento.P2;
  const p3 = kpiDisponivel ? kpiData.P3 : kpiAtingimento.P3;

  const dadosFiltrados = filtrarPorPeriodo(volumeMensal2025, periodo);

  const fatorPeriodo = periodo === 'MÊS' ? 1 / 12 : periodo === 'TRIMESTRE' ? 3 / 12 : 1;
  const produtosFiltrados = [...produtos].slice(0, 8).map(p => ({
    ...p,
    total:     Math.round(p.total     * fatorPeriodo),
    violacoes: Math.round(p.violacoes * fatorPeriodo),
  }));

  const axisProps = {
    tick: { fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' },
    tickLine: false,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <PageHeader
        title="Centro de Gestão"
        sub="CENTRAL OPERACIONAL AIOPS // NODE: PREDICTFY-01"
        rightSlot={<PeriodoToggle value={periodo} onChange={setPeriodo} />}
      />

      <main style={{ flex: 1, padding: '20px 28px 60px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* ── MODULE 01: OLA Status ──────────────────────────────────────── */}
        <Module n={1} title="Status de OLA"
          sub={`Contagem de violações vs meta SPC · ${PERIODO_LABELS[periodo]}`}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <StatusBanner
              priority="P2"
              violations={kpiDisponivel ? (p2.violacoesAno ?? violacoesReais2025.P2) : violacoesReais2025.P2}
              metaMin={kpiDisponivel ? Math.round((p2.metaAnual ?? 63) * 0.9) : olaTargets.P2.metaViolacoesAno.min}
              metaMax={kpiDisponivel ? (p2.metaAnual ?? 63) : olaTargets.P2.metaViolacoesAno.max}
              ola="≤ 4h"
            />
            <StatusBanner
              priority="P3"
              violations={kpiDisponivel ? (p3.violacoesAno ?? violacoesReais2025.P3) : violacoesReais2025.P3}
              metaMin={kpiDisponivel ? Math.round((p3.metaAnual ?? 280) * 0.9) : olaTargets.P3.metaViolacoesAno.min}
              metaMax={kpiDisponivel ? (p3.metaAnual ?? 280) : olaTargets.P3.metaViolacoesAno.max}
              ola="≤ 12h"
            />
          </div>
        </Module>

        {/* ── MODULE 02: Predictive Forecast ────────────────────────────── */}
        <Module n={2} title="Previsão Preditiva" sub={d1Disponivel ? `${(d1Data.modelo_usado ?? 'modelo').toUpperCase()} · Volume de incidentes D+1 e D+7` : 'MOTOR PREDITIVO · Volume de incidentes D+1 e D+7'}>
          {prevLoading ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
              {[0, 1, 2, 3].map(i => <Skeleton key={i} height={130} />)}
            </div>
          ) : !prevDisponivel ? (
            <SemDados mensagem="Previsão Prophet indisponível — execute o notebook 03" />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
              <KpiCard
                label="Total Incidentes D+1"
                value={d1Data.total ?? '—'}
                sub={d1Data.p2 != null ? `P2: ${d1Data.p2} · P3: ${d1Data.p3}` : `Modelo: ${d1Data.modelo_usado}`}
                color="var(--orange)"
                delay={0}
              />
              <KpiCard
                label="Total Incidentes D+7"
                value={d7Disponivel ? (d7Data.total ?? '—') : '—'}
                sub="Previsão horizonte 7 dias"
                color="var(--yellow)"
                delay={60}
              />
              <KpiCard
                label="Atingimento P2"
                value={`${p2.pctAtingimento}%`}
                sub={`Projeção: ${p2.previsaoFechamento} violações`}
                color="var(--red)"
                delay={120}
              />
              <KpiCard
                label="Atingimento P3"
                value={`${p3.pctAtingimento}%`}
                sub={`Projeção: ${p3.previsaoFechamento} violações`}
                color="var(--green)"
                delay={180}
              />
            </div>
          )}
        </Module>

        {/* ── MODULE 03: Monthly Violations ─────────────────────────────── */}
        <Module
          n={3}
          title="Violações Mensais 2025"
          sub={`P2 (≤4h) e P3 (≤12h) · linha tracejada = meta mensal P2 · ${PERIODO_LABELS[periodo]}`}
        >
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={dadosFiltrados} margin={{ top: 10, right: 16, bottom: 0, left: -10 }} barGap={4}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="mes" {...axisProps} axisLine={{ stroke: 'var(--border)' }} />
              <YAxis {...axisProps} axisLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <ReferenceLine
                y={3.25} stroke="var(--red)" strokeDasharray="4 4" strokeOpacity={0.5}
                label={{ value: 'Meta P2/mês', position: 'right', fill: 'var(--red)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
              />
              <Bar dataKey="violP2" name="Violações P2" fill="var(--red)"    fillOpacity={0.8} radius={[2,2,0,0]} />
              <Bar dataKey="violP3" name="Violações P3" fill="var(--orange)" fillOpacity={0.8} radius={[2,2,0,0]} />
            </BarChart>
          </ResponsiveContainer>
          <Legend items={[['var(--red)', 'Violações P2'], ['var(--orange)', 'Violações P3']]} />
        </Module>

        {/* ── MODULE 04: Volume by Product ──────────────────────────────── */}
        <Module
          n={4}
          title="Volume por Produto"
          sub={`Clique na barra para detalhar em Monitoramento · top 8 produtos · ${PERIODO_LABELS[periodo]}`}
        >
          <ResponsiveContainer width="100%" height={420}>
            <BarChart
              data={produtosFiltrados} layout="vertical"
              margin={{ top: 4, right: 16, bottom: 4, left: 20 }}
              barSize={10}
              onClick={d => { if (d?.activeLabel) navigate('/monitoramento'); }}
              style={{ cursor: 'pointer' }}
            >
              <XAxis type="number" {...axisProps} axisLine={{ stroke: 'var(--border)' }} />
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
                    <div style={{
                      background: 'var(--surface3)', border: '1px solid var(--border-md)',
                      borderRadius: 4, padding: '8px 12px',
                    }}>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)', marginBottom: 6 }}>{label}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--teal)', marginBottom: 2 }}>total: {d?.total}</div>
                      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--red)' }}>violações: {d?.violacoes} ({d?.taxaViolacao}%)</div>
                    </div>
                  );
                }}
                cursor={{ fill: 'rgba(255,255,255,0.03)' }}
              />
              <Bar dataKey="total"     name="Total"     fill="var(--teal)" fillOpacity={0.65} radius={[0,3,3,0]} />
              <Bar dataKey="violacoes" name="Violações" fill="var(--red)"  fillOpacity={0.85} radius={[0,3,3,0]} />
            </BarChart>
          </ResponsiveContainer>
          <Legend items={[['var(--teal)', 'Total'], ['var(--red)', 'Violações']]} />
        </Module>

        {/* ── MODULE 05: Monthly Trend ───────────────────────────────────── */}
        <Module
          n={5}
          title="Tendência Mensal de Incidentes"
          sub={`P2 e P3 · apenas incidentes KPI (prioridade Alta e Média) · ${PERIODO_LABELS[periodo]}`}
        >
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={dadosFiltrados} margin={{ top: 8, right: 16, bottom: 0, left: -10 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="mes" {...axisProps} axisLine={{ stroke: 'var(--border)' }} />
              <YAxis {...axisProps} axisLine={false} />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
              <Line type="monotone" dataKey="P2" name="P2" stroke="var(--red)"    strokeWidth={2} dot={{ r: 3, fill: 'var(--red)',    stroke: 'var(--bg)', strokeWidth: 2 }} />
              <Line type="monotone" dataKey="P3" name="P3" stroke="var(--orange)" strokeWidth={2} dot={{ r: 3, fill: 'var(--orange)', stroke: 'var(--bg)', strokeWidth: 2 }} />
            </LineChart>
          </ResponsiveContainer>
          <Legend items={[['var(--red)', 'P2'], ['var(--orange)', 'P3']]} />
        </Module>

        {/* ── MODULE 06: KPI Atingimento OLA ───────────────────────────────── */}
        <Module
          n={6}
          title="Atingimento de KPI OLA"
          sub={kpiDisponivel
            ? `METODOLOGIA SPC · ${PERIODO_LABELS[periodo]}`
            : `ESTIMATIVAS SIMULADAS · nb07 pendente · ${PERIODO_LABELS[periodo]}`
          }
        >
          {kpiLoading ? (
            <Skeleton height={200} />
          ) : (
            <>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 64, padding: '8px 0' }}>
                <Gauge
                  label="KPI P2"
                  pct={p2.pctAtingimento ?? 83}
                  color={p2.tendencia === 'dentro_da_meta' ? 'var(--green)' : p2.tendencia === 'atencao' ? 'var(--orange)' : 'var(--red)'}
                  sub={kpiDisponivel
                    ? `${p2.violacoesAno ?? p2.previsaoFechamento} viol. · meta: ${p2.metaAnual ?? 63} · margem: ${p2.margemRestante >= 0 ? '+' : ''}${p2.margemRestante ?? 0}`
                    : `Projeção: ${p2.previsaoFechamento} violações`
                  }
                />
                <Gauge
                  label="KPI P3"
                  pct={p3.pctAtingimento ?? 118}
                  color={p3.tendencia === 'dentro_da_meta' ? 'var(--green)' : p3.tendencia === 'atencao' ? 'var(--orange)' : 'var(--red)'}
                  sub={kpiDisponivel
                    ? `${p3.violacoesAno ?? p3.previsaoFechamento} viol. · meta: ${p3.metaAnual ?? 280} · margem: ${p3.margemRestante >= 0 ? '+' : ''}${p3.margemRestante ?? 0}`
                    : `Projeção: ${p3.previsaoFechamento} violações`
                  }
                />
              </div>

              <div style={{
                textAlign: 'center', marginTop: 10,
                fontFamily: 'var(--font-mono)', fontSize: 11,
                color: 'var(--text-sec)', letterSpacing: '0.04em',
              }}>
                {kpiDisponivel
                  ? `P2: ${p2.pctUtilizado ?? 66.7}% da cota utilizada · P3: ${p3.pctUtilizado ?? 73.6}% da cota utilizada`
                  : `PREVISÃO FINAL: P2 = ${p2.previsaoFechamento} violações · P3 = ${p3.previsaoFechamento} violações`
                }
              </div>

              {kpiDisponivel && (p2.mesesAnomalos?.length > 0 || p3.mesesAnomalos?.length > 0) && (
                <div style={{
                  marginTop: 14, padding: '10px 16px',
                  background: 'var(--surface3)', borderRadius: 6,
                  border: '1px solid var(--border)',
                  display: 'flex', gap: 24, justifyContent: 'center',
                }}>
                  {[['P2', p2.mesesAnomalos, 'var(--red)'], ['P3', p3.mesesAnomalos, 'var(--orange)']].map(([label, meses, cor]) =>
                    meses?.length > 0 && (
                      <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
                          ANOMALIAS {label}:
                        </span>
                        <div style={{ display: 'flex', gap: 4 }}>
                          {meses.map(m => (
                            <span key={m} style={{
                              fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
                              color: cor, background: `${cor}18`,
                              border: `1px solid ${cor}44`,
                              borderRadius: 3, padding: '1px 6px',
                            }}>{m}</span>
                          ))}
                        </div>
                      </div>
                    )
                  )}
                </div>
              )}
            </>
          )}
        </Module>

      </main>
    </div>
  );
}
