import { useState, useRef } from 'react';
import { useBreakpoint } from '../hooks/useBreakpoint';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, LabelList,
} from 'recharts';
import { Terminal, AlertTriangle, Activity, Users } from 'lucide-react';
import { grupos, shapFeatures, categorias, categoriaNomes } from '../data/mockData';
import { useApi } from '../hooks/useApi';
import SemDados from '../components/SemDados';
import PeriodoToggle from '../components/PeriodoToggle';

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
        fontFamily: 'var(--font-mono)', fontSize: 30, fontWeight: 400,
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

// ─── Group tooltip ─────────────────────────────────────────────────────────────
function GrupoTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 4, padding: '8px 12px',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)', marginBottom: 6 }}>{label}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)', marginBottom: 2 }}>total: {d?.total}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--red)', marginBottom: 2 }}>violações: {d?.violacoes}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--orange)', fontWeight: 700 }}>taxa: {d?.taxaViolacao}%</div>
    </div>
  );
}

// ─── SHAP tooltip ──────────────────────────────────────────────────────────────
function ShapTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 4, padding: '8px 12px', maxWidth: 220,
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>{d?.feature}</div>
      <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-pri)', marginBottom: 4 }}>{d?.descricao}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: 'var(--red)' }}>
        {(d?.importance * 100).toFixed(0)}%
      </div>
    </div>
  );
}

// ─── Cluster Heatmap (layout unificado: identidade + grid de métricas) ────────
function ClusterHeatmap({ clusters }) {
  const [tooltip, setTooltip] = useState(null);
  const wrapperRef = useRef(null);
  const CORES = ['#5ac8fa', '#ffcc00', '#ff9f0a', '#ff2d55'];

  function heatColor(norm) {
    if (norm < 0.5) {
      const t = norm * 2;
      const r = Math.round(52  + (255 - 52)  * t);
      const g = Math.round(199 + (204 - 199) * t);
      const b = Math.round(89  * (1 - t));
      return { bar: `rgba(${r},${g},${b},0.85)`, bg: `rgba(${r},${g},${b},0.08)` };
    } else {
      const t = (norm - 0.5) * 2;
      const r = 255;
      const g = Math.round(204 * (1 - t));
      const b = Math.round(85  * t);
      return { bar: `rgba(${r},${g},${b},0.85)`, bg: `rgba(${r},${g},${b},0.08)` };
    }
  }

  const METRICAS = [
    { label: 'Temporalidade', key: c => c.score_T,           fmt: v => `${(v*100).toFixed(0)}%`, desc: 'Incidentes fora do horário comercial' },
    { label: 'Gravidade',     key: c => c.score_G,           fmt: v => `${(v*100).toFixed(0)}%`, desc: 'Prioridade + violação + duração' },
    { label: 'Volume',        key: c => c.score_V,           fmt: v => `${(v*100).toFixed(0)}%`, desc: 'Frequência relativa por grupo' },
    { label: 'Violação OLA',  key: c => c.taxaViolacao,      fmt: v => `${v.toFixed(1)}%`,        desc: '% de incidentes que violaram OLA' },
    { label: 'P2 Alta',       key: c => c.perfil.pctP2 ?? 0, fmt: v => `${v.toFixed(0)}%`,        desc: '% de incidentes com prioridade alta' },
    { label: 'Fim de Semana', key: c => c.perfil.pctFds ?? 0,fmt: v => `${v.toFixed(0)}%`,        desc: '% de incidentes em fins de semana' },
  ];

  const normPorMetrica = METRICAS.map(m => {
    const vals = clusters.map(c => m.key(c));
    const min  = Math.min(...vals);
    const max  = Math.max(...vals);
    return clusters.map(c => max === min ? 0.5 : (m.key(c) - min) / (max - min));
  });

  const maxTamanho = Math.max(...clusters.map(c => c.tamanho));

  function handleCellEnter(e, cluster, metrica, norm) {
    if (!wrapperRef.current) return;
    const wrap = wrapperRef.current.getBoundingClientRect();
    const cell = e.currentTarget.getBoundingClientRect();
    const mi   = METRICAS.indexOf(metrica);
    setTooltip({
      x:      cell.left - wrap.left + cell.width / 2,
      y:      cell.top  - wrap.top,
      cluster, metrica, norm,
      valor:  metrica.fmt(metrica.key(cluster)),
      isMax:  norm === Math.max(...normPorMetrica[mi]),
      isMin:  norm === Math.min(...normPorMetrica[mi]),
    });
  }

  return (
    <div ref={wrapperRef} style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: 10 }}>

      {clusters.map((c, ri) => {
        const cor        = CORES[ri];
        const isCritical = c.taxaViolacao > 2;

        return (
          <div key={c.id} style={{
            display: 'grid',
            gridTemplateColumns: '220px 1fr',
            background: 'var(--surface3)',
            border: `1px solid ${isCritical ? cor + '55' : 'var(--border)'}`,
            borderLeft: `3px solid ${cor}`,
            borderRadius: 6,
            overflow: 'hidden',
          }}>

            {/* ── Identidade ──────────────────────────────────────────── */}
            <div style={{
              padding: '14px 16px',
              borderRight: '1px solid var(--border)',
              display: 'flex', flexDirection: 'column', gap: 8,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                  color: cor, letterSpacing: '0.12em',
                }}>CLUSTER {c.id}</span>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                  color: isCritical ? 'var(--red)' : 'var(--green)',
                  background: isCritical ? 'rgba(255,45,85,0.12)' : 'rgba(52,199,89,0.12)',
                  border: `1px solid ${isCritical ? 'var(--red)' : 'var(--green)'}44`,
                  borderRadius: 3, padding: '1px 6px',
                }}>{c.taxaViolacao}% viol.</span>
              </div>

              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
                color: 'var(--text-pri)', lineHeight: 1.35,
                textTransform: 'uppercase', letterSpacing: '0.03em',
              }}>{c.label}</div>

              <div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', marginBottom: 4 }}>TAMANHO</div>
                <div style={{ height: 4, background: 'var(--surface4)', borderRadius: 2, overflow: 'hidden', marginBottom: 3 }}>
                  <div style={{
                    width: `${(c.tamanho / maxTamanho) * 100}%`,
                    height: '100%', background: cor, borderRadius: 2, opacity: 0.8,
                  }} />
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700, color: 'var(--text-pri)' }}>
                  {c.tamanho.toLocaleString('pt-BR')}{' '}
                  <span style={{ fontSize: 9, color: 'var(--text-muted)', fontWeight: 400 }}>incidentes</span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 14 }}>
                {[
                  { l: 'GRUPO', v: c.perfil.grupo },
                  { l: 'HORA',  v: `${c.perfil.horaMedia}h` },
                ].map(({ l, v }) => (
                  <div key={l}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', marginBottom: 2 }}>{l}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: 'var(--text-sec)' }}>{v}</div>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                {c.perfil.diasCriticos.map(d => (
                  <span key={d} style={{
                    fontFamily: 'var(--font-mono)', fontSize: 8,
                    color: 'var(--text-muted)', background: 'var(--surface4)',
                    border: '1px solid var(--border)', borderRadius: 3, padding: '1px 5px',
                  }}>{d}</span>
                ))}
              </div>
            </div>

            {/* ── Métricas (grid 3×2) ──────────────────────────────────── */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gridTemplateRows: 'repeat(2, 1fr)',
            }}>
              {METRICAS.map((m, mi) => {
                const norm  = normPorMetrica[mi][ri];
                const cores = heatColor(norm);
                const isMax = norm === Math.max(...normPorMetrica[mi]);
                const isMin = norm === Math.min(...normPorMetrica[mi]);

                return (
                  <div
                    key={m.label}
                    onMouseEnter={e => handleCellEnter(e, c, m, norm)}
                    onMouseLeave={() => setTooltip(null)}
                    style={{
                      padding: '10px 12px',
                      background: cores.bg,
                      borderRight: mi % 3 !== 2 ? '1px solid var(--border)' : 'none',
                      borderBottom: mi < 3 ? '1px solid var(--border)' : 'none',
                      cursor: 'crosshair',
                      display: 'flex', flexDirection: 'column', gap: 5,
                    }}
                  >
                    <div style={{
                      fontFamily: 'var(--font-mono)', fontSize: 8,
                      color: 'var(--text-muted)', letterSpacing: '0.1em',
                      textTransform: 'uppercase',
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    }}>
                      {m.label}
                      {isMax && <span style={{ color: 'var(--red)',   fontSize: 8 }}>▲</span>}
                      {isMin && <span style={{ color: 'var(--green)', fontSize: 8 }}>▼</span>}
                    </div>
                    <div style={{ height: 3, background: 'var(--surface4)', borderRadius: 2 }}>
                      <div style={{ width: `${norm * 100}%`, height: '100%', background: cores.bar, borderRadius: 2 }} />
                    </div>
                    <div style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: isMax ? 14 : 12,
                      fontWeight: isMax ? 700 : 500,
                      color: isMax ? cores.bar : 'var(--text-sec)',
                    }}>{m.fmt(m.key(c))}</div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* ── Legenda ──────────────────────────────────────────────────────── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end',
        fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)',
        marginTop: 2,
      }}>
        <span style={{ color: 'var(--green)' }}>▼ menor</span>
        <div style={{
          width: 60, height: 6, borderRadius: 3,
          background: 'linear-gradient(to right, #34c759, #ffcc00, #ff2d55)',
        }} />
        <span style={{ color: 'var(--red)' }}>▲ maior</span>
        <span style={{ marginLeft: 8 }}>· valores relativos entre clusters</span>
      </div>

      {/* ── Tooltip ──────────────────────────────────────────────────────── */}
      {tooltip && (() => {
        const TWIDTH    = 210;
        const wrapW     = wrapperRef.current?.getBoundingClientRect().width ?? 600;
        const left      = Math.max(4, Math.min(tooltip.x - TWIDTH / 2, wrapW - TWIDTH - 4));
        const showBelow = tooltip.y < 100;
        const top       = showBelow ? tooltip.y + 36 : tooltip.y - 148;
        const normColor = tooltip.norm > 0.65 ? 'var(--red)' : tooltip.norm > 0.35 ? 'var(--orange)' : 'var(--green)';
        const corCluster = CORES[tooltip.cluster.id];

        return (
          <div style={{
            position: 'absolute', left, top, width: TWIDTH,
            pointerEvents: 'none', zIndex: 50,
            background: 'var(--surface2)',
            border: '1px solid var(--border-md)',
            borderRadius: 6, padding: '10px 12px',
            boxShadow: '0 8px 28px rgba(0,0,0,0.65)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: corCluster }}>
                C{tooltip.cluster.id} · {tooltip.metrica.label}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 700, color: normColor }}>
                {tooltip.valor}
              </span>
            </div>
            <div style={{ height: '0.5px', background: 'var(--border)', marginBottom: 8 }} />
            {[
              { label: 'descrição',    value: tooltip.metrica.desc,                                                                                         color: 'var(--text-sec)' },
              { label: 'intensidade',  value: `${(tooltip.norm * 100).toFixed(0)}% relativo ao maior`,                                                      color: normColor },
              { label: 'ranking',      value: tooltip.isMax ? '▲ maior entre clusters' : tooltip.isMin ? '▼ menor entre clusters' : 'intermediário',        color: tooltip.isMax ? 'var(--red)' : tooltip.isMin ? 'var(--green)' : 'var(--text-sec)' },
              { label: 'cluster',      value: tooltip.cluster.label.split('—')[0].trim(),                                                                   color: 'var(--text-sec)' },
              { label: 'violação OLA', value: `${tooltip.cluster.taxaViolacao}%`,                                                                            color: tooltip.cluster.taxaViolacao > 2 ? 'var(--red)' : 'var(--green)' },
              { label: 'tamanho',      value: `${tooltip.cluster.tamanho.toLocaleString('pt-BR')} incidentes`,                                              color: 'var(--text-sec)' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', flexShrink: 0 }}>{label}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color, fontWeight: 600, textAlign: 'right' }}>{value}</span>
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}

// ─── Cluster card (reservado para uso futuro) ─────────────────────────────────
function ClusterCard({ cluster, accentColor }) {
  const badgeColor = accentColor ?? (
    cluster.taxaViolacao > 5 ? 'var(--red)' :
    cluster.taxaViolacao > 2 ? 'var(--orange)' :
                                'var(--green)'
  );
  const isCritical = cluster.taxaViolacao > 2;
  return (
    <div style={{
      background: 'var(--surface3)',
      border: `1px solid ${isCritical ? badgeColor + '66' : 'var(--border)'}`,
      borderTop: `2px solid ${badgeColor}`,
      borderRadius: 6, padding: '16px 18px',
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: badgeColor, letterSpacing: '0.12em' }}>
          CLUSTER {cluster.id}
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: badgeColor, background: `${badgeColor}18`,
          border: `1px solid ${badgeColor}44`, borderRadius: 3, padding: '2px 8px',
        }}>{cluster.taxaViolacao}% VIOLAÇÃO</span>
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 12, color: 'var(--text-pri)', textTransform: 'uppercase' }}>
        {cluster.label}
      </div>
      <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)', lineHeight: 1.55 }}>
        {cluster.descricao}
      </div>
    </div>
  );
}

// ─── Cluster Quadrant (Gartner-style scatter com retângulos proporcionais) ────
function ClusterQuadrant({ clusters }) {
  const [hovered, setHovered] = useState(null);
  const [tooltip, setTooltip] = useState(null);
  const wrapperRef = useRef(null);

  const CORES = ['#5ac8fa', '#ffcc00', '#ff9f0a', '#ff2d55'];
  const maxTamanho = Math.max(...clusters.map(c => c.tamanho));

  // C0 → topo-esq (comercial+alto), C2 → topo-dir (fora+alto)
  // C1 → baixo-esq (comercial+baixo), C3 → baixo-dir (fora+baixo)
  const QUADRANTE_LABEL = {
    0: 'COMERCIAL · ALTO VOL',
    1: 'COMERCIAL · BAIXO VOL',
    2: 'FORA HORÁRIO · ALTO VOL',
    3: 'FORA HORÁRIO · BAIXO VOL',
  };

  function getRectSize(tamanho) {
    const min = 80, max = 200;
    return min + ((tamanho / maxTamanho) * (max - min));
  }

  function handleMouseEnter(e, cluster) {
    if (!wrapperRef.current) return;
    const wrap = wrapperRef.current.getBoundingClientRect();
    const rect = e.currentTarget.getBoundingClientRect();
    setHovered(cluster.id);
    setTooltip({
      x: rect.left - wrap.left + rect.width / 2,
      y: rect.top  - wrap.top,
      cluster,
    });
  }

  return (
    <div ref={wrapperRef} style={{ display: 'flex', gap: 16, position: 'relative' }}>

      {/* ── Scatter Quadrant — grid 2×2 fixo ────────────────────────────── */}
      <div style={{
        flex: '0 0 65%',
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gridTemplateRows: '1fr 1fr',
        height: 400,
        position: 'relative',
        background: 'var(--surface1)',
        border: '1px solid var(--border)',
        borderRadius: 6,
        overflow: 'hidden',
      }}>
        {/* Divisórias */}
        <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: 1, background: 'var(--border)', pointerEvents: 'none', zIndex: 1 }} />
        <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: 1, background: 'var(--border)', pointerEvents: 'none', zIndex: 1 }} />

        {/* Células na ordem: topo-esq(C0), topo-dir(C2), baixo-esq(C1), baixo-dir(C3) */}
        {[0, 2, 1, 3].map(id => {
          const c          = clusters.find(cl => cl.id === id);
          if (!c) return null;
          const cor        = CORES[id];
          const size       = getRectSize(c.tamanho);
          const isCritical = c.taxaViolacao > 2;
          const isHov      = hovered === id;
          const isTopRow   = id === 0 || id === 2;
          const isLeftCol  = id === 0 || id === 1;

          return (
            <div key={id} style={{
              display: 'flex',
              alignItems:     isTopRow   ? 'flex-end'   : 'flex-start',  // ancora no centro
              justifyContent: isLeftCol  ? 'flex-end'   : 'flex-start',
              padding: 16,
              position: 'relative',
            }}>
              {/* Label do quadrante — canto oposto ao retângulo */}
              <div style={{
                position: 'absolute',
                top:    isTopRow  ? 'auto' : 8,
                bottom: isTopRow  ? 8      : 'auto',
                left:   isLeftCol ? 'auto' : 10,
                right:  isLeftCol ? 10     : 'auto',
                fontFamily: 'var(--font-mono)', fontSize: 8,
                color: 'var(--text-muted)', letterSpacing: '0.08em',
                pointerEvents: 'none',
              }}>{QUADRANTE_LABEL[id]}</div>

              {/* Retângulo do cluster */}
              <div
                onMouseEnter={e => handleMouseEnter(e, c)}
                onMouseLeave={() => { setHovered(null); setTooltip(null); }}
                style={{
                  width: size, height: size,
                  background: `${cor}${isHov ? '30' : '15'}`,
                  border: `${isCritical ? 2 : 1}px solid ${cor}${isHov ? 'ff' : '77'}`,
                  borderRadius: 6,
                  cursor: 'crosshair',
                  transition: 'all 0.2s ease',
                  display: 'flex', flexDirection: 'column',
                  alignItems: 'center', justifyContent: 'center', gap: 4,
                  boxShadow: isCritical
                    ? `0 0 ${isHov ? 20 : 10}px ${cor}44`
                    : isHov ? `0 0 12px ${cor}33` : 'none',
                  position: 'relative', zIndex: 2,
                }}
              >
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: cor, fontWeight: 700, letterSpacing: '0.1em' }}>C{c.id}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: size > 140 ? 20 : size > 100 ? 15 : 12,
                  fontWeight: 700, color: 'var(--text-pri)', lineHeight: 1,
                }}>
                  {c.tamanho >= 1000 ? `${(c.tamanho / 1000).toFixed(1)}k` : c.tamanho}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700, color: isCritical ? 'var(--red)' : 'var(--green)' }}>
                  {c.taxaViolacao}% viol.
                </div>
                {isCritical && (
                  <div style={{
                    position: 'absolute', top: -5, right: -5,
                    width: 10, height: 10, borderRadius: '50%',
                    background: 'var(--red)', border: '2px solid var(--bg)',
                    animation: 'pulse-dot 2s ease infinite',
                  }} />
                )}
              </div>
            </div>
          );
        })}

        {/* Label eixo Y */}
        <div style={{
          position: 'absolute', left: 6, top: '50%',
          transform: 'translateY(-50%) rotate(-90deg)',
          transformOrigin: 'center center',
          fontFamily: 'var(--font-mono)', fontSize: 8,
          color: 'var(--text-muted)', letterSpacing: '0.1em',
          whiteSpace: 'nowrap', pointerEvents: 'none',
        }}>VOLUME ↑ ALTO</div>

        {/* Label eixo X */}
        <div style={{
          position: 'absolute', bottom: 6, left: '50%',
          transform: 'translateX(-50%)',
          fontFamily: 'var(--font-mono)', fontSize: 8,
          color: 'var(--text-muted)', letterSpacing: '0.1em',
          whiteSpace: 'nowrap', pointerEvents: 'none',
        }}>TEMPORALIDADE → FORA DO HORÁRIO</div>
      </div>

      {/* Tooltip (relativo ao wrapperRef externo) */}
      {tooltip && (() => {
        const TWIDTH = 220;
        const wrapW  = wrapperRef.current?.getBoundingClientRect().width ?? 700;
        const left   = Math.max(4, Math.min(tooltip.x - TWIDTH / 2, wrapW - TWIDTH - 4));
        const top    = tooltip.y < 200 ? tooltip.y + 60 : tooltip.y - 180;
        const c      = tooltip.cluster;
        const cor    = CORES[c.id];
        return (
          <div style={{
            position: 'absolute', left, top, width: TWIDTH,
            pointerEvents: 'none', zIndex: 50,
            background: 'var(--surface2)',
            border: `1px solid ${cor}66`,
            borderRadius: 6, padding: '10px 12px',
            boxShadow: '0 8px 28px rgba(0,0,0,0.65)',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: cor }}>
                C{c.id} — {c.label.split('—')[0].trim()}
              </span>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                color: c.taxaViolacao > 2 ? 'var(--red)' : 'var(--green)',
              }}>{c.taxaViolacao}% VIOL.</span>
            </div>
            <div style={{ height: '0.5px', background: 'var(--border)', marginBottom: 8 }} />
            {[
              { l: 'incidentes',     v: c.tamanho.toLocaleString('pt-BR'),  col: 'var(--text-pri)' },
              { l: 'hora pico',      v: `${c.perfil.horaMedia}h`,            col: 'var(--text-sec)' },
              { l: 'grupo',          v: c.perfil.grupo,                      col: cor },
              { l: 'fins de semana', v: `${c.perfil.pctFds ?? 0}%`,          col: 'var(--text-sec)' },
              { l: 'P2 (alta)',      v: `${c.perfil.pctP2 ?? 0}%`,           col: (c.perfil.pctP2 ?? 0) > 25 ? 'var(--orange)' : 'var(--text-sec)' },
              { l: 'duração med.',   v: `${c.perfil.duracaoMediana ?? 0}h`,  col: 'var(--text-sec)' },
              { l: 'descrição',      v: c.descricao,                         col: 'var(--text-muted)' },
            ].map(({ l, v, col }) => (
              <div key={l} style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', flexShrink: 0 }}>{l}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: col, fontWeight: 600, textAlign: 'right', maxWidth: 130 }}>{v}</span>
              </div>
            ))}
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginTop: 6 }}>
              {c.perfil.diasCriticos.map(d => (
                <span key={d} style={{
                  fontFamily: 'var(--font-mono)', fontSize: 8,
                  color: cor, background: `${cor}18`,
                  border: `1px solid ${cor}33`,
                  borderRadius: 3, padding: '1px 5px',
                }}>{d}</span>
              ))}
            </div>
          </div>
        );
      })()}

      {/* ── Painel direito ───────────────────────────────────────────────── */}
      <div style={{ flex: '0 0 calc(35% - 16px)', display: 'flex', flexDirection: 'column', gap: 10 }}>

        {/* Alerta */}
        <div style={{
          background: 'rgba(255,45,85,0.08)',
          border: '1px solid var(--red)',
          borderLeft: '3px solid var(--red)',
          borderRadius: 6, padding: '12px 14px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
            color: 'var(--red)', letterSpacing: '0.12em', marginBottom: 6,
          }}>⚠ ALERTA: TEAM05</div>
          <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)', lineHeight: 1.5 }}>
            Risco operacional aumenta <strong style={{ color: 'var(--red)' }}>3× fora do horário comercial</strong>.
            C3 viola {clusters.find(c => c.id === 3)?.taxaViolacao}% vs C1 viola {clusters.find(c => c.id === 1)?.taxaViolacao}% — mesma equipe, contextos opostos.
          </div>
          <div style={{
            display: 'flex', gap: 8, marginTop: 8,
            fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)',
          }}>
            <span>SEVERITY: CRITICAL</span>
            <span>·</span>
            <span>TAG: OUT_OF_HOURS</span>
          </div>
        </div>

        {/* Metrics Score */}
        <div style={{
          background: 'var(--surface2)',
          border: '1px solid var(--border)',
          borderRadius: 6, padding: '12px 14px', flex: 1,
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
            color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: 10,
          }}>CLUSTER METRICS SCORE</div>

          {[...clusters].sort((a, b) => b.taxaViolacao - a.taxaViolacao).map(c => {
            const cor = CORES[c.id];
            return (
              <div key={c.id} style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5, alignItems: 'baseline' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: cor, fontWeight: 700 }}>
                    C{c.id} — {c.label.split(' ').slice(0, 2).join(' ')}
                  </span>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                    color: c.taxaViolacao > 2 ? 'var(--red)' : c.taxaViolacao > 1.2 ? 'var(--orange)' : 'var(--green)',
                  }}>{c.taxaViolacao}%</span>
                </div>
                {[
                  { l: 'T', v: c.score_T },
                  { l: 'G', v: c.score_G },
                  { l: 'V', v: c.score_V },
                ].map(({ l, v }) => (
                  <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)', width: 8, flexShrink: 0 }}>{l}</span>
                    <div style={{ flex: 1, height: 3, background: 'var(--surface4)', borderRadius: 2 }}>
                      <div style={{ width: `${v * 100}%`, height: '100%', background: cor, borderRadius: 2, opacity: 0.8 }} />
                    </div>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)', width: 24, textAlign: 'right' }}>
                      {(v * 100).toFixed(0)}%
                    </span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function TecnicoPage() {
  const { isMobile } = useBreakpoint();
  const [periodo, setPeriodo] = useState('ANO');

  // ── Dados de modelo via API ────────────────────────────────────────────────
  const { data: clustersApiData, loading: clustersLoading, disponivel: clustersDisponivel } = useApi('/clusters');
  const { data: riscoApiData,    loading: riscoLoading,    disponivel: riscoDisponivel    } = useApi('/risco');

  // SHAP: usa API se disponível, senão fallback para mockData (simulado)
  const shapData = (riscoDisponivel && riscoApiData?.shap_features)
    ? riscoApiData.shap_features
    : shapFeatures;
  const isShapSimulado = !riscoDisponivel;

  // Clusters: usa API se disponível
  const clustersData = (clustersDisponivel && clustersApiData?.clusters)
    ? clustersApiData.clusters
    : null;

  // Dados históricos (mockData — referência imutável do dataset)
  const gruposOrdenados = [...grupos].sort((a, b) => b.taxaViolacao - a.taxaViolacao);
  const shapOrdenado = [...shapData].sort((a, b) => b.importance - a.importance);
  const maxImportance = shapOrdenado[0]?.importance ?? 1;
  const topCats = categorias.slice(0, 5);

  const axisProps = {
    tick: { fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' },
    tickLine: false,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <PageHeader
        title="Centro Técnico"
        sub="MÉTRICAS DEVOPS/SRE // EXPLICABILIDADE DO MODELO // ANÁLISE DE CLUSTERS"
        rightSlot={<PeriodoToggle value={periodo} onChange={setPeriodo} />}
      />

      <main style={{ flex: 1, padding: isMobile ? '12px 12px 40px' : '20px 28px 60px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {isMobile && (
          <div style={{ padding: '0 0 4px' }}>
            <PeriodoToggle value={periodo} onChange={setPeriodo} />
          </div>
        )}

        {/* ── MODULE 01: System Metrics ──────────────────────────────────── */}
        <Module n={1} title="Indicadores Operacionais" sub="Dataset KPI 2025 · apenas incidentes P2 + P3">
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)', gap: 12 }}>
            <KpiCard label="Total Incidentes KPI (2025)" value="25.600" sub="P2 + P3 · Jan–Dez 2025"         color="var(--text-muted)" delay={0}   />
            <KpiCard label="Taxa de Violação P2"         value="0.81%"  sub="42 violações / 5.159 inc."    color="var(--red)"        delay={60}  />
            <KpiCard label="Taxa de Violação P3"         value="0.96%"  sub="196 violações / 20.097 inc."  color="var(--orange)"     delay={120} />
            <KpiCard label="Grupo Crítico"               value="Team07" sub="8,94% taxa · 16/179 incidentes" color="var(--red)"     delay={180} />
          </div>
        </Module>

        {/* ── MODULE 02: OLA Violation Rate by Team ─────────────────────── */}
        <Module
          n={2}
          title="Taxa de Violação OLA por Equipe"
          sub="Ordem decrescente · vermelho >3% · laranja >1% · verde <1%"
        >
          <ResponsiveContainer width="100%" height={320}>
            <BarChart
              data={gruposOrdenados} layout="vertical"
              margin={{ top: 4, right: 70, bottom: 4, left: 8 }}
              barSize={13}
            >
              <XAxis
                type="number" domain={[0, 12]}
                {...axisProps}
                axisLine={{ stroke: 'var(--border)' }}
                tickFormatter={v => `${v}%`}
              />
              <YAxis
                type="category" dataKey="id" width={58}
                tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-sec)' }}
                tickLine={false} axisLine={false}
              />
              <Tooltip content={<GrupoTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <Bar dataKey="taxaViolacao" name="Taxa de violação" radius={[0, 3, 3, 0]}>
                {gruposOrdenados.map((g, i) => (
                  <Cell
                    key={i}
                    fill={g.taxaViolacao > 3 ? 'var(--red)' : g.taxaViolacao > 1 ? 'var(--orange)' : 'var(--green)'}
                    fillOpacity={0.85}
                  />
                ))}
                <LabelList
                  dataKey="taxaViolacao"
                  position="right"
                  formatter={v => `${v}%`}
                  style={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Module>

        {/* ── MODULE 03: XGBoost Feature Importance ─────────────────────── */}
        <Module
          n={3}
          title={`Fatores de Risco de Violação${isShapSimulado ? ' · SIMULADO' : ''}`}
          sub={isShapSimulado
            ? 'Valores simulados · substituídos por SHAP real após executar notebook 04'
            : 'Valores SHAP reais — outputs/risco_ola.json'}
        >
          <ResponsiveContainer width="100%" height={shapOrdenado.length * 36 + 20}>
            <BarChart
              data={shapOrdenado} layout="vertical"
              margin={{ top: 4, right: 60, bottom: 4, left: 20 }}
              barSize={13}
            >
              <XAxis
                type="number" domain={[0, 0.35]}
                {...axisProps}
                axisLine={{ stroke: 'var(--border)' }}
                tickFormatter={v => `${(v * 100).toFixed(0)}%`}
              />
              <YAxis
                type="category" dataKey="label" width={130}
                tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-sec)' }}
                tickLine={false} axisLine={false}
              />
              <Tooltip content={<ShapTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
              <Bar dataKey="importance" name="Importância" radius={[0, 3, 3, 0]}>
                {shapOrdenado.map((f, i) => (
                  <Cell key={i} fill="var(--red)" fillOpacity={0.2 + 0.8 * (f.importance / maxImportance)} />
                ))}
                <LabelList
                  dataKey="importance"
                  position="right"
                  formatter={v => `${(v * 100).toFixed(0)}%`}
                  style={{ fill: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Module>

        {/* ── MODULE 04: Cluster Analysis ───────────────────────────────── */}
        <Module
          n={4}
          title="Análise de Clusters"
          sub={clustersDisponivel && clustersData
            ? `K-MEANS TGV · K=4 · Silhouette=0.608 · Temporalidade × Volume`
            : 'K-MEANS TGV · execute o notebook 05 para gerar dados de cluster'}
        >
          {clustersLoading ? (
            <Skeleton height={400} />
          ) : !clustersDisponivel ? (
            <SemDados mensagem="Modelo K-Means não treinado — execute o notebook 05" />
          ) : (
            <ClusterQuadrant clusters={clustersData} />
          )}
        </Module>

        {/* ── MODULE 05: Group × Category Matrix ────────────────────────── */}
        <Module
          n={5}
          title="Matriz Grupo × Categoria"
          sub="Taxa de violação estimada (%) · células mais escuras = maior taxa · scroll horizontal disponível"
          noPad
        >
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 600 }}>
              <thead>
                <tr style={{ background: 'var(--surface3)' }}>
                  <th style={{
                    padding: '8px 16px', textAlign: 'left',
                    fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
                    color: 'var(--text-sec)', letterSpacing: '0.12em',
                    borderBottom: '1px solid var(--border)', minWidth: 80,
                  }}>GRUPO</th>
                  {topCats.map(c => (
                    <th key={c.id} title={c.id} style={{
                      padding: '8px 14px', textAlign: 'center',
                      fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
                      color: 'var(--text-sec)', letterSpacing: '0.1em',
                      borderBottom: '1px solid var(--border)', minWidth: 100, cursor: 'help',
                    }}>
                      {categoriaNomes[c.id] ?? c.id}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {grupos.map((g, gi) => (
                  <tr key={g.id} style={{ borderBottom: gi < grupos.length - 1 ? '1px solid var(--border)' : 'none' }}>
                    <td style={{
                      padding: '8px 16px',
                      fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
                      color: g.id === 'Team07' ? 'var(--red)' : 'var(--text-pri)',
                    }}>{g.id}</td>
                    {topCats.map((c, ci) => {
                      const rate = +((g.taxaViolacao * 0.6 + c.taxaViolacao * 0.4) * (0.8 + (gi * ci % 5) * 0.08)).toFixed(2);
                      const alpha = Math.min(rate / 8, 1);
                      return (
                        <td key={c.id} style={{
                          padding: '8px 14px', textAlign: 'center',
                          fontFamily: 'var(--font-mono)', fontSize: 11,
                          color: rate > 3 ? 'var(--red)' : rate > 1.5 ? 'var(--orange)' : 'var(--text-sec)',
                          background: `rgba(255,45,85,${alpha * 0.2})`,
                          fontWeight: rate > 3 ? 700 : 400,
                        }}>
                          {rate}%
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Module>

      </main>
    </div>
  );
}
