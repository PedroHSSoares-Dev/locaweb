import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { heatmapData, clusters } from '../data/mockData';

// Find the busiest day for a given product/group and return its hourly distribution
function getHourlyDistribution(item) {
  // Use all days, aggregate heatmapData into hourly totals (simplified for product/group)
  // Aggregate all days weighted by a seed from the item name
  const seed = item.produto?.charCodeAt(0) ?? item.id?.charCodeAt(4) ?? 0;
  const dayIndex = seed % heatmapData.length;
  return heatmapData[dayIndex].horas.map((v, h) => ({
    hora: `${h}h`,
    value: v,
  }));
}

function getTopClusters(item) {
  const name = item.produto ?? item.id ?? '';
  return clusters
    .filter(c =>
      c.perfil.produtos.some(p => p === name) ||
      c.perfil.grupo === name
    )
    .concat(clusters.filter(c =>
      !c.perfil.produtos.some(p => p === name) &&
      c.perfil.grupo !== name
    ))
    .slice(0, 3);
}

function HoraTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 4, padding: '6px 10px',
      fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-pri)',
    }}>
      {label}: {payload[0].value}
    </div>
  );
}

export default function DrillDownPanel({ item, onClose }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (item) requestAnimationFrame(() => setVisible(true));
    return () => setVisible(false);
  }, [item]);

  const handleClose = () => {
    setVisible(false);
    setTimeout(onClose, 230);
  };

  if (!item) return null;

  const name = item.produto ?? item.id ?? '—';
  const hourly = getHourlyDistribution(item);
  const topClusters = getTopClusters(item);
  const maxHora = Math.max(...hourly.map(h => h.value));

  const taxaColor =
    (item.taxaViolacao > 1.5 || item.probViolacao > 30) ? 'var(--red)' :
    (item.taxaViolacao > 0.8 || item.probViolacao > 15) ? 'var(--orange)' :
    'var(--green)';

  return (
    <>
      {/* Overlay */}
      <div
        onClick={handleClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 200,
          background: 'rgba(0,0,0,0.6)',
          backdropFilter: 'blur(2px)',
          opacity: visible ? 1 : 0,
          transition: 'opacity 0.22s ease',
        }}
      />

      {/* Panel */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 201,
        width: 400,
        background: 'var(--surface1)',
        borderLeft: '1px solid var(--border-md)',
        display: 'flex', flexDirection: 'column',
        transform: visible ? 'translateX(0)' : 'translateX(40px)',
        opacity: visible ? 1 : 0,
        transition: 'transform 0.22s cubic-bezier(0.16,1,0.3,1), opacity 0.22s ease',
        overflowY: 'auto',
      }}>

        {/* Header */}
        <div style={{
          padding: '18px 20px 14px',
          borderBottom: '1px solid var(--border)',
          position: 'sticky', top: 0,
          background: 'var(--surface1)', zIndex: 1,
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
            <div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontWeight: 700,
                fontSize: 16, color: 'var(--text-pri)', marginBottom: 4,
                letterSpacing: '-0.01em',
              }}>
                {name}
              </div>
              <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-muted)' }}>
                {item.produto ? 'Produto' : 'Grupo de atendimento'}
              </div>
            </div>
            <button
              onClick={handleClose}
              style={{
                padding: 6, borderRadius: 6,
                color: 'var(--text-sec)', border: '1px solid var(--border)',
                display: 'flex', alignItems: 'center', transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-pri)'; e.currentTarget.style.borderColor = 'var(--border-md)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-sec)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
            >
              <X size={14} />
            </button>
          </div>

          {/* Stats row */}
          <div style={{
            marginTop: 14, display: 'flex', gap: 12,
          }}>
            {[
              { label: 'total', value: item.total ?? item.incidentesPendentes ?? '—' },
              { label: 'violações', value: item.violacoes ?? item.criticos ?? '—', color: 'var(--red)' },
              { label: item.taxaViolacao != null ? 'taxa' : 'prob. OLA', value: item.taxaViolacao != null ? `${item.taxaViolacao}%` : `${item.probViolacao}%`, color: taxaColor },
            ].map(s => (
              <div key={s.label} style={{
                flex: 1, background: 'var(--surface2)', border: '1px solid var(--border)',
                borderRadius: 6, padding: '10px 12px',
              }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', marginBottom: 4 }}>{s.label}</div>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 18, fontWeight: 700,
                  color: s.color ?? 'var(--text-pri)', lineHeight: 1,
                }}>{s.value}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Distribuição por hora */}
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10,
              color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: 12,
            }}>
              DISTRIBUIÇÃO POR HORA DO DIA
            </div>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={hourly} margin={{ top: 4, right: 8, bottom: 0, left: -20 }} barSize={8}>
                <XAxis
                  dataKey="hora"
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 8, fill: 'var(--text-muted)' }}
                  tickLine={false} axisLine={{ stroke: 'var(--border)' }}
                  interval={5}
                />
                <YAxis tick={false} axisLine={false} />
                <Tooltip content={<HoraTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                <Bar dataKey="value" radius={[2,2,0,0]}>
                  {hourly.map((h, i) => (
                    <Cell
                      key={i}
                      fill="#E8002D"
                      fillOpacity={0.15 + 0.75 * (h.value / maxHora)}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Top 3 clusters */}
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10,
              color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: 12,
            }}>
              TOP 3 CLUSTERS RELACIONADOS
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {topClusters.map(c => {
                const badgeColor = c.taxaViolacao > 5 ? 'var(--red)' : c.taxaViolacao > 2 ? 'var(--orange)' : 'var(--green)';
                return (
                  <div key={c.id} style={{
                    background: 'var(--surface2)', border: '1px solid var(--border)',
                    borderRadius: 6, padding: '10px 12px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: 'var(--text-pri)' }}>
                        Cluster {c.id}
                      </span>
                      <span style={{
                        fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
                        color: badgeColor, background: `${badgeColor}18`,
                        border: `1px solid ${badgeColor}44`,
                        borderRadius: 3, padding: '1px 7px',
                      }}>{c.taxaViolacao}% violação</span>
                    </div>
                    <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 600, color: 'var(--text-sec)', marginBottom: 4 }}>
                      {c.label}
                    </div>
                    <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.4 }}>
                      {c.descricao}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
