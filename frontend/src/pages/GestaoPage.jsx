import { useState, useEffect, useRef } from 'react';
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
import { useBreakpoint } from '../hooks/useBreakpoint';
import SemDados from '../components/SemDados';
import PeriodoToggle from '../components/PeriodoToggle';

// ─── Identidade visual P2 / P3 ────────────────────────────────────────────────
const COR_P2 = 'var(--teal)';
const COR_P3 = '#ffcc00';
const COR_P2_DIM = 'rgba(90,200,250,0.15)';
const COR_P3_DIM = 'rgba(255,204,0,0.15)';

// ─── Hook: animação de número com easing easeOutExpo ─────────────────────────
function useCountUp(target, duration = 1000) {
  const [value, setValue] = useState(target);
  const rafRef = useRef(null);
  const prevRef = useRef(target);

  useEffect(() => {
    if (target == null) { setValue(null); return; }
    const from = prevRef.current ?? target;
    const start = performance.now();
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(function tick(now) {
      const elapsed = now - start;
      const t = Math.min(elapsed / duration, 1);
      const ease = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
      setValue(Math.round(from + (target - from) * ease));
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
      else prevRef.current = target;
    });
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);

  return value;
}

function useCountUpFloat(target, duration = 1000) {
  const [value, setValue] = useState(target);
  const rafRef = useRef(null);
  const prevRef = useRef(target);

  useEffect(() => {
    if (target == null) { setValue(null); return; }
    const from = prevRef.current ?? target;
    const start = performance.now();
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(function tick(now) {
      const elapsed = now - start;
      const t = Math.min(elapsed / duration, 1);
      const ease = t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
      setValue(+(from + (target - from) * ease).toFixed(1));
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
      else prevRef.current = target;
    });
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);

  return value;
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────
function Skeleton({ height = 80 }) {
  return <div className="skeleton" style={{ height }} />;
}

// ─── Page header ──────────────────────────────────────────────────────────────
function PageHeader({ title, sub, rightSlot }) {
  const { isMobile } = useBreakpoint();
  return (
    <div style={{
      padding: isMobile ? '12px 16px 12px 56px' : '16px 28px',
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
          fontFamily: 'var(--font-mono)', fontSize: isMobile ? 13 : 18, fontWeight: 600,
          color: 'var(--text-pri)', letterSpacing: '0.08em', textTransform: 'uppercase',
        }}>{title}</div>
        {!isMobile && sub && (
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 11,
            color: 'var(--text-sec)', marginTop: 3, letterSpacing: '0.08em',
          }}>{sub}</div>
        )}
      </div>
      {!isMobile && rightSlot && <div>{rightSlot}</div>}
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
function StatusBanner({ priority, violations, metaMin, metaMax, ola, pctUtilizado }) {
  const animViolations = useCountUp(violations);
  const animPct = useCountUpFloat(pctUtilizado);
  const ok = violations <= metaMax;
  const color = ok ? 'var(--green)' : 'var(--red)';
  const dimBg = ok ? 'var(--green-dim)' : 'var(--red-dim)';
  return (
    <div style={{
      background: dimBg, border: `1px solid ${color}`,
      borderRadius: 6, padding: '18px 22px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      transition: 'background 0.3s ease, border-color 0.3s ease',
    }}>
      <div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
          color: 'var(--text-sec)', letterSpacing: '0.12em',
          textTransform: 'uppercase', marginBottom: 6,
        }}>KPI {priority} · OLA {ola}</div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 36, fontWeight: 400,
            color, lineHeight: 1,
          }}>{animViolations}</div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color, opacity: 0.7 }}>
            violações
          </span>
          {animPct != null && (
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600,
              color, opacity: 0.85, marginLeft: 4,
            }}>
              · {animPct}% da cota
            </span>
          )}
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-sec)', marginTop: 6,
        }}>META: {metaMin}–{metaMax} · ANO 2025</div>
      </div>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
        color, background: dimBg, border: `1px solid ${color}`,
        borderRadius: 3, padding: '4px 10px', letterSpacing: '0.1em',
        transition: 'color 0.3s ease, border-color 0.3s ease',
      }}>{ok ? 'DENTRO DA META' : 'ACIMA DA META'}</span>
    </div>
  );
}

// ─── Chart tooltip ────────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const limiarP2 = 5.2;
  const limiarP3 = 23.4;
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 4, padding: '8px 12px',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)', marginBottom: 6 }}>{label}</div>
      {payload.filter(p => p.value != null).map((p, i) => {
        const limiar = p.dataKey === 'violP2' ? limiarP2 : limiarP3;
        const acima = p.value > limiar;
        return (
          <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: acima ? 'var(--red)' : (p.color || p.fill), marginBottom: 2 }}>
            {p.name}: {p.value}{acima ? ' ⚠ acima do limiar' : ''}
          </div>
        );
      })}
    </div>
  );
}

// ─── Gauge donut ──────────────────────────────────────────────────────────────
function Gauge({ label, pct, color, sub, size = 160 }) {
  const capped = Math.min(pct, 100);
  const innerRadius = Math.round(size * 0.325);
  const outerRadius = Math.round(size * 0.45);
  const fontSize = Math.round(size * 0.16);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={[{ value: capped }, { value: 100 - capped }]}
              cx="50%" cy="50%"
              innerRadius={innerRadius} outerRadius={outerRadius}
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
            fontFamily: 'var(--font-mono)', fontSize, fontWeight: 400,
            color, lineHeight: 1,
          }}>{pct}%</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: Math.round(size * 0.065), color: 'var(--text-muted)', marginTop: 3 }}>
            UTILIZADO
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
  'MÊS': 'Dez/2025',
  'TRIMESTRE': 'Q4 2025 · Out–Dez',
  'ANO': 'Jan–Dez 2025',
};

function filtrarPorPeriodo(dados, periodo) {
  if (periodo === 'MÊS') return dados.slice(11, 12);
  if (periodo === 'TRIMESTRE') return dados.slice(9, 12);
  return dados;
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function GestaoPage() {
  const navigate = useNavigate();
  const { isMobile, isTablet } = useBreakpoint();
  const [periodo, setPeriodo] = useState('ANO');
  const [filtroViolacoes, setFiltroViolacoes] = useState('AMBOS');

  // ── Dados de modelo via API ────────────────────────────────────────────────
  const { data: d1Data, loading: d1Loading, disponivel: d1Disponivel } = useApi('/previsoes/d1');
  const { data: d7Data, disponivel: d7Disponivel } = useApi('/previsoes/d7');
  const PERIODO_API = { 'MÊS': 'mes', 'TRIMESTRE': 'trimestre', 'ANO': 'ano' };
  const { data: kpiData, loading: kpiLoading, disponivel: kpiDisponivel } = useApi('/kpi', {
    periodo: PERIODO_API[periodo] ?? 'ano',
  });

  const prevLoading = d1Loading;
  const prevDisponivel = d1Disponivel;

  // Fallback para mockData enquanto kpi_atingimento.json não existe
  const p2 = kpiDisponivel ? kpiData.P2 : kpiAtingimento.P2;
  const p3 = kpiDisponivel ? kpiData.P3 : kpiAtingimento.P3;

  const dadosFiltrados = filtrarPorPeriodo(volumeMensal2025, periodo);

  const dadosGrafico03 = dadosFiltrados.map(d => ({
    mes: d.mes,
    violP2: filtroViolacoes !== 'P3' ? d.violP2 : null,
    violP3: filtroViolacoes !== 'P2' ? d.violP3 : null,
    _violP2orig: d.violP2,
    _violP3orig: d.violP3,
  }));

  const fatorPeriodo = periodo === 'MÊS' ? 1 / 12 : periodo === 'TRIMESTRE' ? 3 / 12 : 1;
  const produtosFiltrados = [...produtos].slice(0, 8).map(p => ({
    ...p,
    total: Math.round(p.total * fatorPeriodo),
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

      <main style={{ flex: 1, padding: isMobile ? '12px 12px 40px' : '20px 28px 60px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {isMobile && (
          <div style={{ padding: '0 0 4px' }}>
            <PeriodoToggle value={periodo} onChange={setPeriodo} />
          </div>
        )}

        {/* ── MODULE 01: OLA Status ──────────────────────────────────────── */}
        <Module n={1} title="Violações vs Meta"
          sub={`Contagem de violações vs meta SPC · ${PERIODO_LABELS[periodo]}`}>
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 12 }}>
            <StatusBanner
              priority="P2"
              violations={kpiDisponivel ? (p2.violacoesAno ?? violacoesReais2025.P2) : violacoesReais2025.P2}
              metaMin={kpiDisponivel ? Math.round((p2.metaAnual ?? 63) * 0.9) : olaTargets.P2.metaViolacoesAno.min}
              metaMax={kpiDisponivel ? (p2.metaAnual ?? 63) : olaTargets.P2.metaViolacoesAno.max}
              pctUtilizado={kpiDisponivel ? p2.pctUtilizado : null}
              ola="≤ 4h"
            />
            <StatusBanner
              priority="P3"
              violations={kpiDisponivel ? (p3.violacoesAno ?? violacoesReais2025.P3) : violacoesReais2025.P3}
              metaMin={kpiDisponivel ? Math.round((p3.metaAnual ?? 280) * 0.9) : olaTargets.P3.metaViolacoesAno.min}
              metaMax={kpiDisponivel ? (p3.metaAnual ?? 280) : olaTargets.P3.metaViolacoesAno.max}
              pctUtilizado={kpiDisponivel ? p3.pctUtilizado : null}
              ola="≤ 12h"
            />
          </div>
        </Module>

        {/* ── MODULE 02 + 03: KPI + Previsão (lado a lado) ─────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: isMobile || isTablet ? '1fr' : '1fr 1fr', gap: 24 }}>

          {/* ── MODULE 02: KPI Atingimento OLA ──────────────────────────────── */}
          <Module
            n={2}
            title="Cota OLA Utilizada"
            sub={kpiDisponivel
              ? `METODOLOGIA SPC · ${PERIODO_LABELS[periodo]}`
              : `ESTIMATIVAS SIMULADAS · nb07 pendente · ${PERIODO_LABELS[periodo]}`
            }
          >
            {kpiLoading ? (
              <Skeleton height={200} />
            ) : (
              <>
                <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', alignItems: 'center', justifyContent: 'center', gap: isMobile ? 24 : 64, padding: '8px 0' }}>
                  <Gauge
                    label="KPI P2"
                    size={120}
                    pct={kpiDisponivel ? p2.pctUtilizado : kpiAtingimento.P2.pctAtingimento}
                    color={kpiDisponivel
                      ? (p2.pctUtilizado > 100 ? 'var(--red)' : p2.pctUtilizado > 85 ? 'var(--orange)' : 'var(--green)')
                      : 'var(--red)'
                    }
                    sub={kpiDisponivel
                      ? `${p2.violacoesAno} viol. · meta ${p2.metaAnual} · margem ${p2.margemRestante >= 0 ? '+' : ''}${p2.margemRestante}`
                      : `Projeção: ${kpiAtingimento.P2.previsaoFechamento} violações`
                    }
                  />
                  <Gauge
                    label="KPI P3"
                    size={120}
                    pct={kpiDisponivel ? p3.pctUtilizado : kpiAtingimento.P3.pctAtingimento}
                    color={kpiDisponivel
                      ? (p3.pctUtilizado > 100 ? 'var(--red)' : p3.pctUtilizado > 85 ? 'var(--orange)' : 'var(--green)')
                      : 'var(--green)'
                    }
                    sub={kpiDisponivel
                      ? `${p3.violacoesAno} viol. · meta ${p3.metaAnual} · margem ${p3.margemRestante >= 0 ? '+' : ''}${p3.margemRestante}`
                      : `Projeção: ${kpiAtingimento.P3.previsaoFechamento} violações`
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
                    : `PREVISÃO FINAL: P2 = ${kpiAtingimento.P2.previsaoFechamento} · P3 = ${kpiAtingimento.P3.previsaoFechamento} violações`
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

          {/* ── MODULE 03: Previsão Preditiva ─────────────────────────────── */}
          <Module n={3} title="Volume Previsto" sub={d1Disponivel ? `${(d1Data.modelo_usado ?? 'modelo').toUpperCase()} · Volume de incidentes D+1 e D+7` : 'MOTOR PREDITIVO · Volume de incidentes D+1 e D+7'}>
            {prevLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {[0, 1].map(i => <Skeleton key={i} height={130} />)}
              </div>
            ) : !prevDisponivel ? (
              <SemDados mensagem="Previsão indisponível — execute o notebook 03" />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <KpiCard
                  label="Total Incidentes D+1"
                  value={d1Data?.total ?? '—'}
                  sub={d1Disponivel ? (d1Data.p2 != null ? `P2: ${d1Data.p2} · P3: ${d1Data.p3}` : 'LSTM indisponível') : 'LSTM indisponível'}
                  color="var(--orange)"
                  delay={0}
                />
                <KpiCard
                  label="Total Incidentes D+7"
                  value={d7Disponivel ? (d7Data?.total ?? '—') : '—'}
                  sub="Previsão horizonte 7 dias"
                  color="var(--yellow)"
                  delay={60}
                />
              </div>
            )}
          </Module>

        </div>

        {/* ── MODULE 04: Violações Mensais ──────────────────────────────── */}
        <Module
            n={4}
            title="Histórico de Violações"
            sub={`P2 (≤4h) e P3 (≤12h) · linha = meta mensal SPC · ${PERIODO_LABELS[periodo]}`}
            action={
              <div style={{ display: 'flex', background: 'var(--surface3)', border: '1px solid var(--border)', borderRadius: 6, padding: 2, gap: 2 }}>
                {['P2', 'P3', 'AMBOS'].map(op => {
                  const ativo = filtroViolacoes === op;
                  const corAtiva = op === 'P2' ? COR_P2 : op === 'P3' ? COR_P3 : 'var(--text-pri)';
                  const bgAtiva = op === 'P2' ? COR_P2_DIM : op === 'P3' ? COR_P3_DIM : 'rgba(255,255,255,0.1)';
                  return (
                    <button
                      key={op}
                      onClick={() => setFiltroViolacoes(op)}
                      style={{
                        fontFamily: 'var(--font-mono)', fontSize: 9,
                        fontWeight: ativo ? 700 : 400,
                        letterSpacing: '0.1em',
                        color: ativo ? corAtiva : 'var(--text-sec)',
                        background: ativo ? bgAtiva : 'transparent',
                        border: ativo ? `1px solid ${corAtiva}` : '1px solid transparent',
                        borderRadius: 4,
                        padding: '3px 10px', cursor: 'pointer',
                        transition: 'all 0.15s',
                      }}
                    >
                      {op}
                    </button>
                  );
                })}
              </div>
            }
          >
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={dadosGrafico03} margin={{ top: 10, right: 16, bottom: 0, left: -10 }} barGap={4}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="mes" {...axisProps} axisLine={{ stroke: 'var(--border)' }} />
                <YAxis {...axisProps} axisLine={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                {(filtroViolacoes === 'P2' || filtroViolacoes === 'AMBOS') && (
                  <ReferenceLine
                    y={kpiDisponivel ? p2.metaMensal : 3.25}
                    stroke={COR_P2} strokeDasharray="4 4" strokeOpacity={0.6}
                  />
                )}
                {(filtroViolacoes === 'P3' || filtroViolacoes === 'AMBOS') && (
                  <ReferenceLine
                    y={kpiDisponivel ? p3.metaMensal : 21.9}
                    stroke={COR_P3} strokeDasharray="4 4" strokeOpacity={0.6}
                  />
                )}
                <Bar
                  dataKey="violP2" name="Violações P2"
                  radius={[2, 2, 0, 0]}
                  isAnimationActive animationBegin={0} animationDuration={500} animationEasing="ease-out"
                >
                  {dadosGrafico03.map((entry, index) => {
                    const limiar = kpiDisponivel ? p2.metaMensal : 3.25;
                    const ultrapassou = entry._violP2orig > limiar;
                    return <Cell key={index} fill={ultrapassou ? 'var(--red)' : COR_P2} fillOpacity={0.85} />;
                  })}
                </Bar>
                <Bar
                  dataKey="violP3" name="Violações P3"
                  radius={[2, 2, 0, 0]}
                  isAnimationActive animationBegin={0} animationDuration={500} animationEasing="ease-out"
                >
                  {dadosGrafico03.map((entry, index) => {
                    const limiar = kpiDisponivel ? p3.metaMensal : 21.9;
                    const ultrapassou = entry._violP3orig > limiar;
                    return <Cell key={index} fill={ultrapassou ? 'var(--red)' : COR_P3} fillOpacity={0.85} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <Legend items={[
              ...(filtroViolacoes !== 'P3' ? [[COR_P2, 'P2 — dentro do limiar']] : []),
              ...(filtroViolacoes !== 'P2' ? [[COR_P3, 'P3 — dentro do limiar']] : []),
              [['var(--red)', 'Acima do limiar SPC']],
            ]} />
          </Module>

          {/* ── MODULE 05: Volume por Produto ─────────────────────────────── */}
          <Module
            n={5}
            title="Incidentes por Produto"
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
                <Bar dataKey="total" name="Total" fill="var(--teal)" fillOpacity={0.65} radius={[0, 3, 3, 0]} />
                <Bar dataKey="violacoes" name="Violações" fill="var(--red)" fillOpacity={0.85} radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <Legend items={[['var(--teal)', 'Total'], ['var(--red)', 'Violações']]} />
          </Module>

          {/* ── MODULE 06: Tendência Mensal ───────────────────────────────── */}
          <Module
            n={6}
            title="Tendência Mensal"
            sub={`P2 e P3 · apenas incidentes KPI (prioridade Alta e Média) · ${PERIODO_LABELS[periodo]}`}
          >
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={dadosFiltrados} margin={{ top: 8, right: 16, bottom: 0, left: -10 }}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="mes" {...axisProps} axisLine={{ stroke: 'var(--border)' }} />
                <YAxis {...axisProps} axisLine={false} />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
                <Line type="monotone" dataKey="P2" name="P2" stroke="var(--red)" strokeWidth={2} dot={{ r: 3, fill: 'var(--red)', stroke: 'var(--bg)', strokeWidth: 2 }} />
                <Line type="monotone" dataKey="P3" name="P3" stroke="var(--orange)" strokeWidth={2} dot={{ r: 3, fill: 'var(--orange)', stroke: 'var(--bg)', strokeWidth: 2 }} />
              </LineChart>
            </ResponsiveContainer>
            <Legend items={[['var(--red)', 'P2'], ['var(--orange)', 'P3']]} />
          </Module>


      </main>
    </div>
  );
}

