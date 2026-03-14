import { useMemo } from 'react';
import {
  ComposedChart, BarChart,
  Bar, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { financialConfig } from '../data/mockData';

const horizonToHours = { '30min': 0.5, '1h': 1, '6h': 6, '12h': 12, '24h': 24 };

const BRL = v =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 }).format(v);

function calcServerFinancials(server, horizon) {
  const cfg = financialConfig;
  const hours = horizonToHours[horizon] ?? 6;
  const p = server.failProb / 100;
  const downtimeLoss = (cfg.revenuePerHourByProduct[server.product] ?? 0) * hours * p;
  const churnLoss =
    (cfg.clientsPerProduct[server.product] ?? 0) * cfg.churnRatePerIncident * cfg.avgClientLTV * p;
  const opsCost = cfg.opsCostPerIncident * (server.failProb >= 80 ? 1 : 0.4);
  const totalRisk = (downtimeLoss + churnLoss + opsCost) * cfg.slaMultiplier;
  return { downtimeLoss, churnLoss, opsCost, totalRisk };
}

// ─── KPI Card (FIX-05: valueColor prop) ──────────────────────────────────────
function FinKpiCard({ label, value, accent, highlight, delay, subtitle, redBorder, valueColor }) {
  return (
    <div style={{
      background: 'var(--surface2)',
      border: redBorder ? '1px solid rgba(232,0,45,0.35)' : '1px solid var(--border)',
      borderRadius: 8,
      padding: '16px 20px',
      display: 'flex', flexDirection: 'column', gap: 6,
      position: 'relative', overflow: 'hidden',
      animation: `fadeInUp 0.4s ease ${delay}ms both`,
      borderTop: `2px solid ${accent}`,
    }}>
      <span style={{
        fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 500,
        color: 'var(--text-sec)', letterSpacing: '0.06em', textTransform: 'uppercase',
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700,
        color: valueColor ?? (highlight ? 'var(--red)' : 'var(--text-pri)'),
        lineHeight: 1, letterSpacing: '-0.02em',
      }}>
        {value}
      </span>
      {subtitle && (
        <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, color: 'var(--text-muted)' }}>
          {subtitle}
        </span>
      )}
    </div>
  );
}

// ─── Tooltip: Visão Geral (ComposedChart) ─────────────────────────────────────
function GeralTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const byKey = Object.fromEntries(payload.map(p => [p.dataKey, p.value]));
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 6, padding: '10px 14px', minWidth: 200,
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 10,
        color: 'var(--text-muted)', marginBottom: 8, letterSpacing: '0.06em',
      }}>
        {label}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 4 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)' }}>
          Exposição total
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: 'var(--red)' }}>
          {BRL(byKey.totalRisk ?? 0)}
        </span>
      </div>
      {byKey.failProb !== undefined && (
        <div style={{
          borderTop: '1px solid var(--border)', marginTop: 6, paddingTop: 6,
          display: 'flex', justifyContent: 'space-between', gap: 16,
        }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
            failProb
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, color: '#fff' }}>
            {byKey.failProb?.toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  );
}

// ─── Tooltip: Visão Técnica (BarChart %) — FIX-01 ────────────────────────────
function TecnicaTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const totalLabel = payload[0]?.payload?.totalLabel;
  return (
    <div style={{
      background: '#1a1a1a', border: '0.5px solid rgba(255,255,255,0.1)',
      padding: '10px 14px', borderRadius: 8,
    }}>
      <p style={{
        color: '#f0f0f0', fontSize: 12, marginBottom: 6,
        fontFamily: 'var(--font-mono)', margin: '0 0 6px',
      }}>
        {label}
      </p>
      {payload.map(p => (
        <p key={p.dataKey} style={{
          color: p.fill, fontSize: 12, margin: '2px 0',
          fontFamily: 'var(--font-mono)',
        }}>
          {p.name}: {p.value?.toFixed(1)}%
        </p>
      ))}
      <p style={{
        color: '#888', fontSize: 11, marginTop: 6, paddingTop: 6,
        borderTop: '0.5px solid rgba(255,255,255,0.07)',
        fontFamily: 'var(--font-mono)', marginBottom: 0,
      }}>
        Total: {totalLabel}
      </p>
    </div>
  );
}

// ─── Product Table ────────────────────────────────────────────────────────────
function ProductTable({ atRisk }) {
  const byProduct = {};
  for (const row of atRisk) {
    if (!byProduct[row.product]) byProduct[row.product] = { servers: 0, totalRisk: 0, maxProb: 0 };
    byProduct[row.product].servers += 1;
    byProduct[row.product].totalRisk += row.totalRisk;
    byProduct[row.product].maxProb = Math.max(byProduct[row.product].maxProb, row.failProb);
  }
  const rows = Object.entries(byProduct).sort((a, b) => b[1].totalRisk - a[1].totalRisk);
  const topProduct = rows[0]?.[0];

  function riskBadge(maxProb) {
    const [color, label] =
      maxProb >= 80 ? ['var(--red)', 'CRÍTICO']
      : maxProb >= 60 ? ['var(--orange)', 'ALTO']
      : ['var(--yellow)', 'MÉDIO'];
    return (
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
        color, background: `${color}18`, border: `1px solid ${color}44`,
        borderRadius: 3, padding: '2px 7px', letterSpacing: '0.08em',
      }}>
        {label}
      </span>
    );
  }

  return (
    <div style={{ overflow: 'hidden', borderRadius: 6, border: '1px solid var(--border)' }}>
      <div style={{
        display: 'grid', gridTemplateColumns: '2fr 1fr 1.6fr 1fr',
        padding: '7px 14px', background: 'var(--surface3)',
        borderBottom: '1px solid var(--border)',
      }}>
        {['PRODUTO', 'SRV EM RISCO', 'EXPOSIÇÃO TOTAL', 'NÍVEL'].map(h => (
          <span key={h} style={{
            fontFamily: 'var(--font-mono)', fontSize: 9,
            color: 'var(--text-muted)', letterSpacing: '0.12em',
          }}>
            {h}
          </span>
        ))}
      </div>
      {rows.map(([product, data]) => (
        <div key={product} style={{
          display: 'grid', gridTemplateColumns: '2fr 1fr 1.6fr 1fr',
          padding: '9px 14px', borderBottom: '1px solid var(--border)',
          borderLeft: product === topProduct ? '3px solid var(--red)' : '3px solid transparent',
          background: product === topProduct ? 'rgba(232,0,45,0.04)' : 'transparent',
          alignItems: 'center',
        }}>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 11,
            fontWeight: product === topProduct ? 600 : 400,
            color: product === topProduct ? 'var(--text-pri)' : 'var(--text-sec)',
          }}>
            {product}
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-sec)' }}>
            {data.servers}
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600,
            color: data.totalRisk > 500000 ? 'var(--red)' : 'var(--text-pri)',
          }}>
            {BRL(data.totalRisk)}
          </span>
          {riskBadge(data.maxProb)}
        </div>
      ))}
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function FinancialImpact({ servers, horizon, viewMode }) {
  const atRisk = useMemo(() =>
    servers
      .filter(s => s.failProb >= 40)
      .map(s => ({ ...s, ...calcServerFinancials(s, horizon) }))
      .sort((a, b) => b.totalRisk - a.totalRisk),
    [servers, horizon]
  );

  const totalDowntime = atRisk.reduce((a, r) => a + r.downtimeLoss, 0);
  const totalChurn    = atRisk.reduce((a, r) => a + r.churnLoss, 0);
  const totalExposure = atRisk.reduce((a, r) => a + r.totalRisk, 0);

  // Geral chart data: absolute values + prob line
  const geralData = atRisk.map(r => ({
    name: r.name,
    failProb: r.failProb,
    totalRisk: Math.round(r.totalRisk),
  }));

  // FIX-01 — Tecnica chart data: pre-calculated percentages
  const tecnicaData = atRisk.map(r => {
    const total = r.downtimeLoss + r.churnLoss + r.opsCost;
    return {
      name: r.name,
      downtimePct: parseFloat(((r.downtimeLoss / total) * 100).toFixed(1)),
      churnPct:    parseFloat(((r.churnLoss    / total) * 100).toFixed(1)),
      opsCostPct:  parseFloat(((r.opsCost      / total) * 100).toFixed(1)),
      failProb:    r.failProb,
      totalLabel:  BRL(r.totalRisk),
    };
  });

  const now = new Date().toLocaleTimeString('pt-BR', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  const legendFormatter = name => ({
    downtimePct: 'Downtime', churnPct: 'Churn', opsCostPct: 'Custo Ops',
    totalRisk: 'Exposição Total', failProb: 'Probabilidade (%)',
  }[name] ?? name);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Page header */}
      <div style={{
        borderLeft: '3px solid var(--green)', paddingLeft: 16,
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
        flexWrap: 'wrap', gap: 8,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
            <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 18, color: 'var(--text-pri)' }}>
              Impacto Financeiro Estimado
            </span>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
              color: 'var(--yellow)', background: 'rgba(255,234,0,0.1)',
              border: '1px solid rgba(255,234,0,0.35)',
              borderRadius: 20, padding: '2px 8px', letterSpacing: '0.1em',
            }}>
              SIMULADO
            </span>
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
            {atRisk.length} servidores em risco · horizonte {horizon} · atualizado {now}
          </div>
        </div>
      </div>

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 16, alignItems: 'start' }}>

        {/* Left column — chart */}
        <div style={{
          background: 'var(--surface1)', border: '1px solid var(--border)',
          borderRadius: 8, padding: '18px 20px',
        }}>
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>
              Exposição por Servidor
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
              {viewMode === 'geral'
                ? 'Exposição total · linha = probabilidade de falha'
                : 'Composição %: downtime + churn + ops cost por servidor'}
            </div>
          </div>

          {/* ── Visão Geral: ComposedChart (bar total + prob line) ─────────── */}
          {viewMode === 'geral' && (
            <ResponsiveContainer width="100%" height={380}>
              <ComposedChart data={geralData} margin={{ top: 8, right: 56, bottom: 28, left: 16 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
                  tickLine={false} axisLine={{ stroke: 'var(--border)' }}
                  angle={-20} textAnchor="end" interval={0} height={44}
                />

                {/* FIX-02 — left Y: label + updated tickFormatter */}
                <YAxis
                  yAxisId="money"
                  orientation="left"
                  tickFormatter={v => 'R$' + (v / 1000).toFixed(0) + 'k'}
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
                  tickLine={false} axisLine={false} width={60}
                  label={{ value: 'Exposição (R$)', angle: -90, position: 'insideLeft', fill: '#888', fontSize: 11 }}
                />

                {/* FIX-02 — right Y: label */}
                <YAxis
                  yAxisId="prob"
                  orientation="right"
                  domain={[0, 100]}
                  tickFormatter={v => `${v}%`}
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
                  tickLine={false} axisLine={false} width={48}
                  label={{ value: 'Probabilidade (%)', angle: 90, position: 'insideRight', fill: '#888', fontSize: 11 }}
                />

                {/* FIX-02 — ReferenceLine with label */}
                <ReferenceLine
                  yAxisId="money"
                  y={500000}
                  stroke="#ffea00"
                  strokeDasharray="4 2"
                  strokeOpacity={0.7}
                  label={{ value: 'Limite R$500k', position: 'insideTopLeft', fill: '#ffea00', fontSize: 11 }}
                />

                <Tooltip content={<GeralTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Legend
                  iconType="square" iconSize={8}
                  wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', paddingTop: 12 }}
                  formatter={legendFormatter}
                />

                <Bar yAxisId="money" dataKey="totalRisk" fill="var(--red)"
                  fillOpacity={0.75} radius={[3, 3, 0, 0]} maxBarSize={52} />
                <Line yAxisId="prob" type="monotone" dataKey="failProb"
                  stroke="#ffffff" strokeWidth={1.5} strokeDasharray="4 2"
                  dot={{ r: 3, fill: '#ffffff', stroke: 'var(--bg)', strokeWidth: 2 }}
                  activeDot={{ r: 4 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}

          {/* ── Visão Técnica: BarChart com % pré-calculados — FIX-01 ─────── */}
          {viewMode === 'tecnica' && (
            <ResponsiveContainer width="100%" height={380}>
              <BarChart data={tecnicaData} margin={{ top: 8, right: 16, bottom: 28, left: 8 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
                  tickLine={false} axisLine={{ stroke: 'var(--border)' }}
                  angle={-20} textAnchor="end" interval={0} height={44}
                />
                <YAxis
                  domain={[0, 100]}
                  tickFormatter={v => v + '%'}
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
                  tickLine={false} axisLine={false} width={40}
                />
                <Tooltip content={<TecnicaTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Legend
                  iconType="square" iconSize={8}
                  wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', paddingTop: 12 }}
                  formatter={legendFormatter}
                />
                <Bar dataKey="downtimePct" stackId="a" fill="#E8002D" name="Downtime" maxBarSize={52} />
                <Bar dataKey="churnPct"    stackId="a" fill="#ff6d00" name="Churn"    maxBarSize={52} />
                <Bar dataKey="opsCostPct"  stackId="a" fill="#ffea00" name="Custo Ops"
                  radius={[3, 3, 0, 0]} maxBarSize={52} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Right column — KPI cards + table */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <FinKpiCard
            label="Exposição Total"
            value={BRL(totalExposure)}
            accent={totalExposure > 500000 ? 'var(--red)' : 'var(--green)'}
            highlight={totalExposure > 500000}
            redBorder={totalExposure > 500000}
            delay={0}
            subtitle="Total consolidado c/ multa SLA"
          />
          <FinKpiCard
            label="Perda por Churn Estimada"
            value={BRL(totalChurn)}
            accent="var(--orange)"
            highlight={totalChurn > 500000}
            delay={60}
            subtitle="Impacto de longo prazo (LTV)"
          />
          {/* FIX-05 — Receita em Risco: valor em amarelo */}
          <FinKpiCard
            label="Receita em Risco"
            value={BRL(totalDowntime)}
            accent="var(--yellow)"
            highlight={false}
            valueColor="#ffea00"
            delay={120}
            subtitle={`Downtime nas próximas ${horizon}`}
          />

          <div style={{
            background: 'var(--surface1)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '14px 16px',
          }}>
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 12, color: 'var(--text-pri)' }}>
                Exposição por Produto
              </div>
              {viewMode === 'tecnica' && (
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                  Produto mais crítico destacado
                </div>
              )}
            </div>
            <ProductTable atRisk={atRisk} />
          </div>
        </div>
      </div>
    </div>
  );
}
