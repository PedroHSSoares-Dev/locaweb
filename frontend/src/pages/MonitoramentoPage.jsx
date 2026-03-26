import { useState, useMemo, useRef } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, ReferenceLine,
} from 'recharts';
import { AlertTriangle, Users, Package, Activity } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import SemDados from '../components/SemDados';
import DrillDownPanel from '../components/DrillDownPanel';

// ─── Skeleton loading placeholder ─────────────────────────────────────────────
function Skeleton({ height = 80 }) {
  return (
    <div style={{
      height,
      background: 'var(--surface2)',
      borderRadius: 8,
      opacity: 0.7,
    }} />
  );
}

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
function Heatmap({ data }) {
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

  const cellW = 28, cellH = 28, labelW = 36;
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const showHours = [0, 6, 12, 18, 23];
  const svgW = labelW + 24 * cellW + 8;
  const svgH = data.length * cellH + 28;

  function cellColor(v) {
    if (!stats) return 'rgba(255,255,255,0.04)';
    const pct = v / stats.maxVal;
    if (pct < 0.15) return 'rgba(255,255,255,0.04)';
    if (pct < 0.35) return `rgba(255,109,0,${(0.2 + pct * 0.4).toFixed(2)})`;
    if (pct < 0.65) return `rgba(255,109,0,${(0.5 + pct * 0.3).toFixed(2)})`;
    return `rgba(232,0,45,${(0.5 + pct * 0.5).toFixed(2)})`;
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
        const diffColor = tooltip.diffMedia > 20 ? '#E8002D' : tooltip.diffMedia > 0 ? '#ff9500' : '#34c759';
        const diffSign  = tooltip.diffMedia >= 0 ? '+' : '';
        const rankTop   = tooltip.total > 0 ? Math.round(tooltip.rank / tooltip.total * 100) : 100;
        const rankColor = tooltip.rank <= 5 ? '#E8002D' : tooltip.rank <= 20 ? '#ff9500' : 'var(--text-sec)';
        const valColor  = stats && tooltip.valor > stats.maxVal * 0.65 ? '#E8002D'
                        : stats && tooltip.valor > stats.maxVal * 0.35 ? '#ff9500' : 'var(--text-pri)';
        return (
          <div style={{
            position: 'absolute', left, top, width: TWIDTH, pointerEvents: 'none', zIndex: 50,
            background: 'var(--surface2, #181818)',
            border: '1px solid var(--border-md, rgba(255,255,255,0.14))',
            borderRadius: 8, padding: '10px 12px',
            boxShadow: '0 8px 28px rgba(0,0,0,0.55)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 7 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: 'var(--text-pri)' }}>
                {tooltip.dia} · {tooltip.hora}h–{tooltip.hora + 1}h
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 15, fontWeight: 700, color: valColor }}>
                {tooltip.valor}
              </span>
            </div>
            <div style={{ height: '0.5px', background: 'var(--border, rgba(255,255,255,0.09))', marginBottom: 8 }} />
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

// ─── Fallback forecast series (Prophet simulado — antes da API) ───────────────

export default function MonitoramentoPage() {
  const [panelItem, setPanelItem] = useState(null);

  // ── Dados de modelo via API ────────────────────────────────────────────────
  const { data: d1Data,       loading: d1Loading,       disponivel: d1Disponivel       } = useApi('/previsoes/d1');
  const { data: serieData,    loading: serieLoading,    disponivel: serieDisponivel    } = useApi('/previsoes/serie');
  const { data: riscoData,    loading: riscoLoading,    disponivel: riscoDisponivel    } = useApi('/risco/produtos');
  const { data: historicoData, loading: historicoLoading, disponivel: historicoDisponivel } = useApi('/historico/diario');
  const { data: sazonalidadeData, disponivel: sazonalidadeDisponivel } = useApi('/historico/sazonalidade');

  // Combina histórico (API) + previsão (API Prophet)
  const volumeComPrevisao = useMemo(() => {
    const hist = (historicoDisponivel && historicoData)
      ? historicoData.map(d => ({ ...d, tipo: 'historico' }))
      : [];
    const prev = (serieDisponivel && serieData?.serie)
      ? serieData.serie.map(d => ({
          dia: d.ds.slice(5).replace('-', '/'), // "2026-01-01" → "01/01"
          P2: d.P2,
          P3: d.P3,
          tipo: 'previsao',
        }))
      : [];
    return [...hist, ...prev];
  }, [historicoData, historicoDisponivel, serieData, serieDisponivel]);

  // Valores D+1 para os KPI cards
  const d1Total = d1Disponivel ? d1Data.total : null;
  const d1P2    = d1Disponivel ? d1Data.p2    : null;
  const d1P3    = d1Disponivel ? d1Data.p3    : null;

  // Tabela de risco — usa API se disponível, senão sem dados
  const riscoList = riscoDisponivel ? riscoData.produtos : null;

  return (
    <main style={{
      flex: 1, padding: '20px 24px 40px',
      display: 'flex', flexDirection: 'column', gap: 16,
      maxWidth: 1600, width: '100%', margin: '0 auto',
    }}>

      {/* ── SEÇÃO 1: KPI Cards ────────────────────────────────────────────── */}
      {d1Loading ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          {[0, 1, 2, 3].map(i => <Skeleton key={i} height={100} />)}
        </div>
      ) : !d1Disponivel ? (
        <SemDados mensagem="Previsão Prophet não disponível — execute o notebook 03" />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          <KpiCard
            label="Incidentes hoje (D+1)"
            value={d1Total}
            sub="previsão Prophet"
            color="var(--orange)"
            Icon={Activity}
            delay={0}
          />
          <KpiCard
            label="P2 em aberto estimado"
            value={d1P2}
            sub="Alta prioridade · OLA 4h"
            color="var(--red)"
            Icon={AlertTriangle}
            delay={50}
          />
          <KpiCard
            label="P3 em aberto estimado"
            value={d1P3}
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
      )}

      {/* ── SEÇÃO 2: Volume diário + previsão ────────────────────────────── */}
      <ChartCard
        title="Volume de incidentes — dez/2025 + previsão D+7"
        sub="Histórico real (02/12–31/12/2025) + previsão Prophet · linha tracejada = previsão"
      >
        {historicoLoading ? (
          <Skeleton height={240} />
        ) : !historicoDisponivel ? (
          <SemDados mensagem="Histórico diário não disponível" />
        ) : null}
        <ResponsiveContainer width="100%" height={historicoLoading || !historicoDisponivel ? 0 : 240}>
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
              x={historicoDisponivel && historicoData?.length
                ? historicoData[historicoData.length - 1].dia
                : '31/12'}
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
        {!sazonalidadeDisponivel ? (
          <SemDados mensagem="Dados de sazonalidade não disponíveis" />
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <div style={{ minWidth: 700 }}>
              <Heatmap data={sazonalidadeData} />
            </div>
          </div>
        )}
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
              {riscoDisponivel ? 'XGBoost — outputs/risco_ola.json' : 'XGBoost pendente · execute o notebook 04'}
            </div>
          </div>
        </div>

        {riscoLoading ? (
          <div style={{ padding: '24px 20px' }}>
            <Skeleton height={120} />
          </div>
        ) : !riscoDisponivel ? (
          <div style={{ padding: '24px 20px' }}>
            <SemDados mensagem="Modelo XGBoost ainda não treinado — execute o notebook 04" />
          </div>
        ) : (
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
              {riscoList.map((r, i) => (
                <tr
                  key={r.produto}
                  style={{
                    background: r.probViolacao > 30 ? 'rgba(232,0,45,0.05)' : r.probViolacao > 15 ? 'rgba(255,234,0,0.04)' : 'transparent',
                    borderBottom: i < riscoList.length - 1 ? '1px solid var(--border)' : 'none',
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
        )}
      </div>

      {panelItem && (
        <DrillDownPanel item={panelItem} onClose={() => setPanelItem(null)} />
      )}
    </main>
  );
}
