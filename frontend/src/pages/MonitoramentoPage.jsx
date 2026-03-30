import { useState, useMemo, useRef } from 'react';
import PeriodoToggle from '../components/PeriodoToggle';
import { useBreakpoint } from '../hooks/useBreakpoint';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from 'recharts';
import { AlertTriangle, Users, Package, Activity } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import SemDados from '../components/SemDados';
import DrillDownPanel from '../components/DrillDownPanel';

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

// ─── KPI Card ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub, color, delay = 0 }) {
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border)',
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
      }}>{value ?? '—'}</div>
      {sub && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-sec)', letterSpacing: '0.04em',
        }}>{sub}</div>
      )}
    </div>
  );
}

// ─── Heatmap SVG custom ───────────────────────────────────────────────────────
function Heatmap({ data }) {
  const { isMobile } = useBreakpoint();
  const [tooltip, setTooltip] = useState(null);
  const wrapperRef = useRef(null);

  const stats = useMemo(() => {
    if (!data?.length) return null;
    const maxVal = data.reduce((m, r) => Math.max(m, ...r.horas), 0);
    const totalPorDia  = data.map(r => r.horas.reduce((a, b) => a + b, 0));
    const totalPorHora = Array.from({ length: 24 }, (_, h) =>
      data.reduce((s, r) => s + r.horas[h], 0)
    );
    const mediaHora = totalPorHora.map(t => Math.round(t / data.length));
    const flat = [];
    data.forEach((r, ri) => r.horas.forEach((v, hi) => flat.push({ ri, hi, v })));
    flat.sort((a, b) => b.v - a.v);
    const rankMap = new Map();
    flat.forEach(({ ri, hi }, idx) => rankMap.set(`${ri}_${hi}`, { rank: idx + 1, total: flat.length }));
    return { maxVal, totalPorDia, totalPorHora, mediaHora, rankMap };
  }, [data]);

  const cellW = isMobile ? 20 : 28, cellH = isMobile ? 20 : 28, labelW = 36;
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const showHours = [0, 6, 12, 18, 23];
  const svgW = labelW + 24 * cellW + 8;
  const svgH = data.length * cellH + 28;

  // teal (low) → orange (mid) → red (high)
  function cellColor(v) {
    if (!stats) return 'rgba(90,200,250,0.04)';
    const pct = v / stats.maxVal;
    if (pct < 0.15) return 'rgba(90,200,250,0.04)';
    if (pct < 0.35) return `rgba(90,200,250,${(0.12 + pct * 0.5).toFixed(2)})`;
    if (pct < 0.65) return `rgba(255,159,10,${(0.3 + pct * 0.4).toFixed(2)})`;
    return `rgba(255,45,85,${(0.45 + pct * 0.5).toFixed(2)})`;
  }

  function handleMouseEnter(e, ri, hi, v) {
    if (!stats || !wrapperRef.current) return;
    const wrapRect = wrapperRef.current.getBoundingClientRect();
    const cellRect = e.currentTarget.getBoundingClientRect();
    const x = cellRect.left - wrapRect.left + cellW / 2;
    const y = cellRect.top  - wrapRect.top;
    const { rank, total } = stats.rankMap.get(`${ri}_${hi}`) || {};
    const pctDia    = stats.totalPorDia[ri]  > 0 ? Math.round(v / stats.totalPorDia[ri]  * 100) : 0;
    const media     = stats.mediaHora[hi];
    const diffMedia = media > 0 ? Math.round((v - media) / media * 100) : 0;
    setTooltip({ x, y, dia: data[ri].dia, hora: hi, valor: v, pctDia, rank, total, media, diffMedia });
  }

  return (
    <div ref={wrapperRef} style={{ position: 'relative' }}>
      <svg width="100%" viewBox={`0 0 ${svgW} ${svgH}`} style={{ overflow: 'visible', display: 'block' }}>
        {hours.map(h => showHours.includes(h) && (
          <text key={h} x={labelW + h * cellW + cellW / 2} y={14} textAnchor="middle"
            style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}>
            {h}h
          </text>
        ))}
        {data.map((row, ri) => (
          <g key={row.dia}>
            <text x={labelW - 6} y={28 + ri * cellH + cellH / 2 + 4} textAnchor="end"
              style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-sec)' }}>
              {row.dia}
            </text>
            {row.horas.map((v, hi) => (
              <rect key={hi}
                x={labelW + hi * cellW + 1} y={28 + ri * cellH + 1}
                width={cellW - 2} height={cellH - 2} rx={3}
                fill={cellColor(v)}
                style={{ cursor: 'crosshair' }}
                onMouseEnter={e => handleMouseEnter(e, ri, hi, v)}
                onMouseLeave={() => setTooltip(null)}
              />
            ))}
          </g>
        ))}
      </svg>

      {tooltip && (() => {
        const TWIDTH   = 215;
        const svgEl    = wrapperRef.current?.querySelector('svg');
        const svgRect  = svgEl?.getBoundingClientRect();
        const wrapRect = wrapperRef.current?.getBoundingClientRect();
        const scaleX   = svgRect ? svgRect.width  / svgW : 1;
        const scaleY   = svgRect ? svgRect.height / svgH  : 1;
        const cellPxX  = (labelW + tooltip.hora * cellW + cellW / 2) * scaleX;
        const cellPxY  = (28 + (data.findIndex(r => r.dia === tooltip.dia)) * cellH) * scaleY;
        const wrapW    = wrapRect?.width ?? 600;
        const left     = Math.max(4, Math.min(cellPxX - TWIDTH / 2, wrapW - TWIDTH - 4));
        const showBelow = cellPxY < 130;
        const top      = showBelow ? cellPxY + cellH * scaleY + 6 : cellPxY - 150;
        const diffColor = tooltip.diffMedia > 20 ? 'var(--red)' : tooltip.diffMedia > 0 ? 'var(--orange)' : 'var(--green)';
        const diffSign  = tooltip.diffMedia >= 0 ? '+' : '';
        const rankTop   = tooltip.total > 0 ? Math.round(tooltip.rank / tooltip.total * 100) : 100;
        const rankColor = tooltip.rank <= 5 ? 'var(--red)' : tooltip.rank <= 20 ? 'var(--orange)' : 'var(--text-sec)';
        const valColor  = stats && tooltip.valor > stats.maxVal * 0.65 ? 'var(--red)'
                        : stats && tooltip.valor > stats.maxVal * 0.35 ? 'var(--orange)' : 'var(--text-pri)';
        return (
          <div style={{
            position: 'absolute', left, top, width: TWIDTH, pointerEvents: 'none', zIndex: 50,
            background: 'var(--surface2)',
            border: '1px solid var(--border-md)',
            borderRadius: 6, padding: '10px 12px',
            boxShadow: '0 8px 28px rgba(0,0,0,0.65)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 7 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: 'var(--text-pri)' }}>
                {tooltip.dia} · {tooltip.hora}h–{tooltip.hora + 1}h
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 15, fontWeight: 700, color: valColor }}>
                {tooltip.valor}
              </span>
            </div>
            <div style={{ height: '0.5px', background: 'var(--border)', marginBottom: 8 }} />
            {[
              { label: '% do dia',                value: `${tooltip.pctDia}% dos incidentes de ${tooltip.dia}`,          color: 'var(--text-sec)' },
              { label: `vs média ${tooltip.hora}h`, value: `${diffSign}${tooltip.diffMedia}% (média: ${tooltip.media})`, color: diffColor },
              { label: 'ranking',                  value: `#${tooltip.rank} de ${tooltip.total} · top ${rankTop}%`,      color: rankColor },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 5 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', flexShrink: 0 }}>{label}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color, fontWeight: 600, textAlign: 'right' }}>{value}</span>
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}

// ─── System Log ───────────────────────────────────────────────────────────────
const LOG_ENTRIES = [
  { time: '04:31:05', level: 'INFO', msg: 'PROPHET_ENGINE: Forecast D+1 generated. MAE: 17.06' },
  { time: '04:31:05', level: 'INFO', msg: 'API_HEALTH: All endpoints operational. TTL: 60s' },
  { time: '04:30:44', level: 'WARN', msg: 'CACHE_INVALIDATED: previsoes_volume.json updated' },
  { time: '04:30:12', level: 'INFO', msg: 'FLOOR_APPLIED: Sat 03/01 yhat=-7.4 → floor=29' },
  { time: '04:29:58', level: 'INFO', msg: 'MODEL_LOADED: prophet_ensemble_v5v6 initialized' },
  { time: '04:29:41', level: 'INFO', msg: 'CACHE_HIT: previsoes_volume.json · age: 18s' },
];

function SystemLog() {
  return (
    <div style={{
      background: 'var(--surface1)', border: '1px solid var(--border)',
      borderRadius: 6, overflow: 'hidden',
    }}>
      <div style={{
        padding: '10px 16px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
          color: 'var(--text-sec)', letterSpacing: '0.1em', textTransform: 'uppercase',
        }}>LOG DO SISTEMA</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--green)',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)', display: 'inline-block', animation: 'pulse-dot 2s ease infinite' }} />
          LIVE_OPS
        </span>
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 11,
        background: 'var(--bg)', padding: '10px 16px',
        display: 'flex', flexDirection: 'column', gap: 5,
      }}>
        {LOG_ENTRIES.map((e, i) => (
          <div key={i} style={{ display: 'flex', gap: 14 }}>
            <span style={{ color: 'var(--teal)', flexShrink: 0 }}>[{e.time}]</span>
            <span style={{ color: e.level === 'WARN' ? 'var(--orange)' : 'var(--text-sec)' }}>{e.msg}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Utils ────────────────────────────────────────────────────────────────────
// Converte "2026-01-15" → "15/01" (mesmo formato DD/MM do histórico diário)
function fmtDia(ds) {
  const [, mes, dia] = ds.split('-');
  return `${dia}/${mes}`;
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function MonitoramentoPage() {
  const { isMobile } = useBreakpoint();
  const [panelItem, setPanelItem] = useState(null);
  const [periodo, setPeriodo] = useState('ANO');

  // ── Dados de modelo via API ────────────────────────────────────────────────
  const { data: d1Data,           loading: d1Loading,       disponivel: d1Disponivel       } = useApi('/previsoes/d1');
  const { data: serieData,        loading: serieLoading,    disponivel: serieDisponivel    } = useApi('/previsoes/serie');
  const { data: riscoData,        loading: riscoLoading,    disponivel: riscoDisponivel    } = useApi('/risco/produtos');
  const { data: historicoData,    loading: historicoLoading, disponivel: historicoDisponivel } = useApi('/historico/diario');
  const { data: sazonalidadeData, disponivel: sazonalidadeDisponivel } = useApi('/historico/sazonalidade');

  // Combina histórico (API) + previsão (API Prophet)
  const volumeComPrevisao = useMemo(() => {
    const hist = (historicoDisponivel && historicoData)
      ? historicoData.map(d => ({ ...d, tipo: 'historico' }))
      : [];
    const prev = (serieDisponivel && serieData?.serie)
      ? serieData.serie.map(d => ({
          dia:  d.dia ?? fmtDia(d.ds),   // usar campo 'dia' se existir (Prophet), senão converter 'ds' (LSTM)
          P2:   d.P2 ?? 0,
          P3:   d.P3 ?? 0,
          tipo: 'previsao',
        }))
      : [];
    return [...hist, ...prev];
  }, [historicoData, historicoDisponivel, serieData, serieDisponivel]);

  // Valores D+1 para os KPI cards
  const d1Total = d1Disponivel ? d1Data.total : null;
  const d1P2    = d1Disponivel ? d1Data.p2    : null;
  const d1P3    = d1Disponivel ? d1Data.p3    : null;

  // Modelo ativo — campo modelo_usado retornado pela API
  const modeloAtivo = d1Disponivel ? (d1Data?.modelo_usado ?? 'prophet_original') : null;
  const maeAtivo    = d1Disponivel ? (d1Data?.mae ?? null) : null;

  const MODELO_META = {
    'lstm_v2':             { label: 'LSTM V2',         cor: 'var(--teal)'      },
    'prophet_mc_ensemble': { label: 'PROPHET MC',       cor: 'var(--orange)'   },
    'prophet_original':    { label: 'PROPHET ORIGINAL', cor: 'var(--text-sec)' },
  };
  const modeloMeta = MODELO_META[modeloAtivo] ?? { label: 'MODELO ATIVO', cor: 'var(--text-sec)' };

  // Tabela de risco — usa API se disponível, senão sem dados
  const riscoList = riscoDisponivel ? riscoData.produtos : null;

  const axisProps = {
    tick: { fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' },
    tickLine: false,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <PageHeader
        title="Centro de Monitoramento"
        sub="CENTRAL OPERACIONAL AIOPS // NODE: PREDICTFY-01"
        rightSlot={<PeriodoToggle value={periodo} onChange={setPeriodo} />}
      />

      <main style={{ flex: 1, padding: isMobile ? '12px 12px 40px' : '20px 28px 60px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {isMobile && (
          <div style={{ padding: '0 0 4px' }}>
            <PeriodoToggle value={periodo} onChange={setPeriodo} />
          </div>
        )}

        {/* ── MODULE 01: D+1 Forecast Metrics ───────────────────────────── */}
        <Module
          n={1}
          title="Previsão do Próximo Dia"
          sub={modeloAtivo
            ? `${modeloMeta.label}${maeAtivo ? ` · MAE: ${typeof maeAtivo === 'number' ? maeAtivo.toFixed(2) : maeAtivo}` : ''} · previsão de volume para o próximo dia`
            : 'PROPHET-ENSEMBLE · previsão de volume para o próximo dia'
          }
        >
          {d1Loading ? (
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)', gap: 12 }}>
              {[0, 1, 2, 3].map(i => <Skeleton key={i} height={130} />)}
            </div>
          ) : !d1Disponivel ? (
            <SemDados mensagem="Previsão Prophet indisponível — execute o notebook 03" />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)', gap: 12 }}>
              <KpiCard
                label="Total Incidentes D+1"
                value={d1Total ?? '—'}
                sub={`Previsão ${modeloMeta.label}`}
                color="var(--orange)"
                delay={0}
              />
              <KpiCard
                label="P2 Estimado em Aberto"
                value={d1P2 ?? '—'}
                sub={d1P2 != null ? 'Alta prioridade · OLA ≤ 4h' : 'Indisponível neste modelo'}
                color="var(--red)"
                delay={60}
              />
              <KpiCard
                label="P3 Estimado em Aberto"
                value={d1P3 ?? '—'}
                sub={d1P3 != null ? 'Média prioridade · OLA ≤ 12h' : 'Indisponível neste modelo'}
                color="var(--yellow)"
                delay={120}
              />
              <KpiCard
                label="Grupo Crítico"
                value="Team07"
                sub="8,94% de taxa de violação"
                color="var(--red)"
                delay={180}
              />
            </div>
          )}
        </Module>

        {/* ── MODULE 02: Incident Volume Timeseries ─────────────────────── */}
        <Module
          n={2}
          title="Volume de Incidentes — Série Temporal"
          sub={modeloAtivo
            ? `MOTOR PREDITIVO: ${modeloMeta.label}${maeAtivo ? ` // MAE: ${typeof maeAtivo === 'number' ? maeAtivo.toFixed(2) : maeAtivo}` : ''} · reais Dez/2025 + previsão Jan/2026`
            : 'MOTOR PREDITIVO: PROPHET-ENSEMBLE // MAE: 17.06 · reais Dez/2025 + previsão Jan/2026'
          }
        >
          {historicoLoading ? (
            <Skeleton height={isMobile ? 220 : 380} />
          ) : !historicoDisponivel ? (
            <SemDados mensagem="Dados históricos indisponíveis" />
          ) : (
            <>
              <ResponsiveContainer width="100%" height={isMobile ? 220 : 380}>
                <AreaChart data={volumeComPrevisao} margin={{ top: 8, right: 16, bottom: 0, left: -10 }}>
                  <defs>
                    <linearGradient id="gradP2" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#ff2d55" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#ff2d55" stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="gradP3" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#5ac8fa" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#5ac8fa" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="dia" {...axisProps} axisLine={{ stroke: 'var(--border)' }} interval={4} />
                  <YAxis {...axisProps} axisLine={false} />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (!active || !payload?.length) return null;
                      const isPrev = payload[0]?.payload?.tipo === 'previsao';
                      return (
                        <div style={{
                          background: 'var(--surface3)', border: '1px solid var(--border-md)',
                          borderRadius: 4, padding: '8px 12px',
                        }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>
                            {label}{isPrev ? ' · PREVISÃO' : ' · REAL'}
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
                    x={historicoDisponivel && historicoData?.length
                      ? historicoData[historicoData.length - 1].dia
                      : '31/12'}
                    stroke="var(--border-hi)"
                    strokeDasharray="6 3"
                    label={{
                      value: '← HISTÓRICO · PREVISÃO →',
                      position: 'insideTopLeft',
                      fill: 'var(--text-muted)', fontSize: 9, fontFamily: 'var(--font-mono)',
                    }}
                  />
                  <Area type="monotone" dataKey="P2" name="P2" stroke="var(--red)"  strokeWidth={2} fill="url(#gradP2)" dot={false} />
                  <Area type="monotone" dataKey="P3" name="P3" stroke="var(--teal)" strokeWidth={2} fill="url(#gradP3)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', gap: 16, marginTop: 8, justifyContent: 'flex-end' }}>
                {[['var(--red)', 'P2'], ['var(--teal)', 'P3']].map(([c, l]) => (
                  <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: c }} />
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)' }}>{l}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Module>

        {/* ── MODULE 03: Seasonality Matrix ─────────────────────────────── */}
        <Module
          n={3}
          title="Matriz de Sazonalidade"
          sub="Concentração de incidentes por hora × dia da semana · 2023–2025 · pico: Qui 11h (391)"
        >
          {!sazonalidadeDisponivel ? (
            <SemDados mensagem="Dados de sazonalidade indisponíveis" />
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <div style={{ minWidth: 700, minHeight: 280 }}>
                <Heatmap data={sazonalidadeData} />
              </div>
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--teal)' }}>BAIXO</span>
            {[
              'rgba(90,200,250,0.04)',
              'rgba(90,200,250,0.22)',
              'rgba(255,159,10,0.45)',
              'rgba(255,45,85,0.60)',
              'rgba(255,45,85,0.90)',
            ].map((c, i) => (
              <div key={i} style={{ width: 24, height: 12, borderRadius: 2, background: c }} />
            ))}
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--red)' }}>ALTO</span>
          </div>
        </Module>

        {/* ── MODULE 04: Predicted SLA Breaches ─────────────────────────── */}
        <Module
          n={4}
          title="Risco de Violação por Produto"
          sub={riscoDisponivel ? 'ATRIBUIÇÃO DE RISCO EM TEMPO REAL POR PRODUTO · XGBoost' : 'XGBOOST PENDENTE · execute o notebook 04'}
          noPad
        >
          {riscoLoading ? (
            <div style={{ padding: '16px' }}><Skeleton height={120} /></div>
          ) : !riscoDisponivel ? (
            <div style={{ padding: '16px' }}>
              <SemDados mensagem="Modelo XGBoost não treinado — execute o notebook 04" />
            </div>
          ) : (
            <>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: 'var(--surface3)' }}>
                    {['PRODUTO', 'INC. PENDENTES', 'RISCO DE VIOLAÇÃO OLA', 'STATUS', ''].map(h => (
                      <th key={h} style={{
                        padding: '8px 16px', textAlign: 'left',
                        fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
                        color: 'var(--text-sec)', letterSpacing: '0.12em',
                        borderBottom: '1px solid var(--border)',
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {riscoList.map((r, i) => {
                    const riskColor = r.probViolacao > 30 ? 'var(--red)' : r.probViolacao > 15 ? 'var(--orange)' : 'var(--green)';
                    return (
                      <tr
                        key={r.produto}
                        style={{
                          background: r.probViolacao > 30 ? 'rgba(255,45,85,0.04)' : r.probViolacao > 15 ? 'rgba(255,159,10,0.03)' : 'transparent',
                          borderBottom: i < riscoList.length - 1 ? '1px solid var(--border)' : 'none',
                        }}
                      >
                        <td style={{ padding: '10px 0 10px 0', paddingLeft: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center' }}>
                            <div style={{ width: 3, height: 36, background: riskColor, borderRadius: 2, marginRight: 14, flexShrink: 0 }} />
                            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: 'var(--text-pri)' }}>
                              {r.produto}
                            </span>
                          </div>
                        </td>
                        <td style={{ padding: '14px 16px', fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-sec)' }}>
                          {r.incidentesPendentes}
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <div style={{ width: 80, height: 3, background: 'var(--surface4)', borderRadius: 2, overflow: 'hidden' }}>
                              <div style={{
                                height: '100%', width: `${r.probViolacao}%`,
                                background: riskColor, borderRadius: 2,
                              }} />
                            </div>
                            <span style={{
                              fontFamily: 'var(--font-mono)', fontSize: 12,
                              fontWeight: 700, color: riskColor,
                            }}>{r.probViolacao}% RISCO</span>
                          </div>
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <span style={{
                            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
                            color: riskColor,
                            background: r.probViolacao > 30 ? 'var(--red-dim)' : r.probViolacao > 15 ? 'var(--orange-dim)' : 'var(--green-dim)',
                            border: `1px solid ${riskColor}44`,
                            borderRadius: 3, padding: '2px 8px', letterSpacing: '0.08em',
                          }}>
                            {r.probViolacao > 30 ? 'ALTO RISCO' : r.probViolacao > 15 ? 'ATENÇÃO' : 'NOMINAL'}
                          </span>
                        </td>
                        <td style={{ padding: '14px 16px' }}>
                          <button
                            onClick={() => setPanelItem(r)}
                            style={{
                              fontFamily: 'var(--font-mono)', fontSize: 11,
                              color: 'var(--text-sec)',
                              border: '1px solid var(--border-hi)',
                              borderRadius: 3, padding: '3px 10px',
                              background: 'transparent',
                              letterSpacing: '0.06em', transition: 'all 0.15s',
                            }}
                            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = 'var(--text-pri)'; }}
                            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-sec)'; }}
                          >
                            [ANALISAR]
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)' }}>
                <button style={{
                  fontFamily: 'var(--font-mono)', fontSize: 11,
                  color: 'var(--text-sec)',
                  border: '1px solid var(--border-hi)',
                  borderRadius: 3, padding: '6px 16px',
                  background: 'transparent', letterSpacing: '0.08em',
                }}>
                  [EXECUTAR MITIGAÇÃO PREDITIVA]
                </button>
              </div>
            </>
          )}
        </Module>

        {/* ── System Log ────────────────────────────────────────────────── */}
        <SystemLog />

      </main>

      {panelItem && (
        <DrillDownPanel item={panelItem} onClose={() => setPanelItem(null)} />
      )}
    </div>
  );
}
