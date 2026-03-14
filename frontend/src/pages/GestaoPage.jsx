import { useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  LineChart, Line, CartesianGrid, PieChart, Pie,
} from 'recharts';
import {
  Activity, CheckCircle, AlertTriangle, DollarSign,
} from 'lucide-react';
import { servers, timeSeriesData, financialConfig, horizonMultiplier } from '../data/mockData';
import { useDashboard } from '../context/DashboardContext';

const PRODUCTS = ['Hospedagem Compartilhada', 'E-mail Pro', 'Cloud Server', 'DNS'];
const horizonToHours = { '30min': 0.5, '1h': 1, '6h': 6, '12h': 12, '24h': 24 };

const BRL = v =>
  new Intl.NumberFormat('pt-BR', {
    style: 'currency', currency: 'BRL', maximumFractionDigits: 0,
  }).format(v);

function calcTotalRisk(servers, horizon) {
  const cfg = financialConfig;
  const mult = horizonMultiplier[horizon]?.financial ?? 1.0;
  const hours = horizonToHours[horizon] ?? 6;
  return servers
    .filter(s => s.failProb >= 40)
    .reduce((sum, s) => {
      const p = s.failProb / 100;
      const downtimeLoss = (cfg.revenuePerHourByProduct[s.product] ?? 0) * hours * p;
      const churnLoss = (cfg.clientsPerProduct[s.product] ?? 0) * cfg.churnRatePerIncident * cfg.avgClientLTV * p;
      const opsCost = cfg.opsCostPerIncident * (s.failProb >= 80 ? 1 : 0.4);
      return sum + (downtimeLoss + churnLoss + opsCost) * cfg.slaMultiplier * mult;
    }, 0);
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────
function GestaoKpi({ icon: Icon, label, value, color, sub, onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--surface1)',
        border: `1px solid ${color}33`,
        borderTop: `2px solid ${color}`,
        borderRadius: 8,
        padding: '20px 24px',
        display: 'flex', flexDirection: 'column', gap: 12,
        cursor: onClick ? 'pointer' : 'default',
        transition: 'border-color 0.2s',
        animation: 'fadeInUp 0.4s ease both',
      }}
      onMouseEnter={e => { if (onClick) e.currentTarget.style.borderColor = color; }}
      onMouseLeave={e => { if (onClick) e.currentTarget.style.borderColor = `${color}33`; }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 500,
          color: 'var(--text-sec)', letterSpacing: '0.07em', textTransform: 'uppercase',
        }}>
          {label}
        </span>
        <span style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: 36, height: 36, borderRadius: 8,
          background: `${color}18`, color,
        }}>
          <Icon size={18} strokeWidth={1.8} />
        </span>
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700,
        color, lineHeight: 1, letterSpacing: '-0.02em',
      }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-muted)' }}>
          {sub}
        </div>
      )}
    </div>
  );
}

// ─── Product bar chart tooltip ─────────────────────────────────────────────────
function ProductTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const ok   = payload.find(p => p.dataKey === 'ok')?.value ?? 0;
  const risk = payload.find(p => p.dataKey === 'risco')?.value ?? 0;
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 6, padding: '8px 12px',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--green)', marginBottom: 2 }}>
        ✓ {ok} ok
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--red)' }}>
        ⚠ {risk} em risco
      </div>
    </div>
  );
}

// ─── Trend tooltip ─────────────────────────────────────────────────────────────
function TrendTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 6, padding: '8px 12px',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>
        {label}
      </div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600, color: 'var(--text-pri)' }}>
        {payload[0].value?.toFixed(1)}% média
      </div>
    </div>
  );
}

// ─── Timeline event severidade ─────────────────────────────────────────────────
function severityBadge(failProb) {
  const [color, label] =
    failProb >= 80 ? ['var(--red)',    'CRÍTICO'] :
    failProb >= 60 ? ['var(--orange)', 'ALERTA']  :
                     ['var(--yellow)', 'ATENÇÃO'];
  return (
    <span style={{
      fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
      color, background: `${color}18`, border: `1px solid ${color}44`,
      borderRadius: 3, padding: '1px 7px', letterSpacing: '0.08em',
    }}>
      {label}
    </span>
  );
}

const ISSUE_PT = {
  queda_servidor:       'Queda de servidor',
  falha_rede:           'Falha de rede',
  esgotamento_recursos: 'Esgotamento de recursos',
};

// Simulate "hours ago" deterministically from failProb
function horasAtras(server, idx) {
  const h = Math.round(1 + (server.failProb % 7) + idx * 1.5);
  return h <= 1 ? 'há 1h' : `há ${Math.min(h, 23)}h`;
}

export default function GestaoPage() {
  const { horizon } = useDashboard();
  const navigate = useNavigate();
  const location = useLocation();

  const mult = horizonMultiplier[horizon]?.prob ?? 1.0;

  const normalCount  = servers.filter(s => s.failProb * mult < 40).length;
  const atRiskNow    = servers.filter(s => s.failProb * mult >= 40).length;
  const healthPct    = +((normalCount / servers.length) * 100).toFixed(1);
  const infraOk      = healthPct >= 80;

  const totalRisk    = useMemo(() => calcTotalRisk(servers, horizon), [horizon]);

  // Product bar data
  const productData = useMemo(() =>
    PRODUCTS.map(product => {
      const group = servers.filter(s => s.product === product);
      return {
        name: product.replace('Hospedagem Compartilhada', 'Hospedagem').replace('Compartilhada', ''),
        fullName: product,
        ok:    group.filter(s => s.failProb * mult < 40).length,
        risco: group.filter(s => s.failProb * mult >= 40).length,
      };
    }), [mult]
  );

  // Trend line: average failProb per hour across timeSeriesData
  const trendData = useMemo(() => {
    const keys = Object.keys(timeSeriesData[0]).filter(k => k !== 'hour');
    return timeSeriesData.map(point => {
      const avg = keys.reduce((s, k) => s + (point[k] ?? 0), 0) / keys.length;
      return { hour: point.hour, avg: +avg.toFixed(1) };
    });
  }, []);

  const trendUp = trendData.slice(-2).reduce((s, p) => s + p.avg, 0) >
                  trendData.slice(0, 2).reduce((s, p) => s + p.avg, 0);
  const trendColor = trendUp ? 'var(--red)' : 'var(--green)';
  const trendLabel = trendUp ? '↑ Piorando' : '↓ Melhorando';

  // Timeline events
  const timelineEvents = useMemo(() =>
    [...servers]
      .filter(s => s.failProb >= 55)
      .sort((a, b) => b.failProb - a.failProb)
      .slice(0, 5)
  , []);

  // Gauge donut data
  const gaugeData = [
    { name: 'Saúde', value: healthPct },
    { name: 'Risco', value: 100 - healthPct },
  ];
  const gaugeColor = healthPct >= 95 ? 'var(--green)' : healthPct >= 80 ? 'var(--yellow)' : 'var(--red)';

  return (
    <div key={location.key} className="page-enter">
      <main style={{
        flex: 1,
        padding: '20px 24px 32px',
        display: 'flex', flexDirection: 'column', gap: 16,
        maxWidth: 1600,
        width: '100%',
        margin: '0 auto',
      }}>

        {/* ── SEÇÃO 1: Health Banner ───────────────────────────────────────── */}
        <div style={{
          borderRadius: 8,
          padding: '16px 24px',
          background: infraOk ? 'rgba(0,230,118,0.07)' : 'rgba(232,0,45,0.08)',
          border: `1px solid ${infraOk ? 'rgba(0,230,118,0.25)' : 'rgba(232,0,45,0.3)'}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          animation: 'fadeInUp 0.3s ease both',
        }}>
          <div>
            <div style={{
              fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 16,
              color: infraOk ? 'var(--green)' : 'var(--red)',
              marginBottom: 4,
            }}>
              {normalCount} de {servers.length} servidores operando normalmente
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
              {atRiskNow} requerem atenção · atualizado agora
            </div>
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 32, fontWeight: 700,
            color: infraOk ? 'var(--green)' : 'var(--red)',
            letterSpacing: '-0.03em',
          }}>
            {healthPct}%
          </div>
        </div>

        {/* ── SEÇÃO 2: KPI Cards ───────────────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
          <GestaoKpi
            icon={Activity}
            label="Uptime da Infra"
            value={`${healthPct}%`}
            color={healthPct >= 95 ? 'var(--green)' : healthPct >= 90 ? 'var(--yellow)' : 'var(--red)'}
            sub="Servidores com failProb < 40%"
          />
          <GestaoKpi
            icon={CheckCircle}
            label="Servidores OK"
            value={`${normalCount} / ${servers.length}`}
            color="var(--green)"
            sub={`failProb < 40% · horizonte ${horizon}`}
          />
          <GestaoKpi
            icon={AlertTriangle}
            label="Em Risco Agora"
            value={atRiskNow}
            color={atRiskNow > 0 ? 'var(--red)' : 'var(--green)'}
            sub={`failProb ≥ 40% ajustado · ${horizon}`}
          />
          <GestaoKpi
            icon={DollarSign}
            label="Exposição Financeira"
            value={BRL(totalRisk)}
            color="var(--yellow)"
            sub="Clique para detalhar"
            onClick={() => navigate('/financeiro')}
          />
        </div>

        {/* ── SEÇÃO 3+4: Product chart + Gauge ────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '60fr 40fr', gap: 16 }}>

          {/* Product bar chart */}
          <div style={{
            background: 'var(--surface1)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '18px 20px',
          }}>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>
                Saúde por Produto
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                Clique na barra para filtrar em Monitoramento
              </div>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={productData}
                layout="vertical"
                margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
                barSize={10}
                onClick={data => {
                  if (data?.activePayload?.[0]) {
                    const fullName = productData.find(p => p.name === data.activeLabel)?.fullName;
                    if (fullName) navigate(`/monitoramento?produto=${encodeURIComponent(fullName)}`);
                  }
                }}
              >
                <XAxis
                  type="number"
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
                  tickLine={false} axisLine={{ stroke: 'var(--border)' }}
                />
                <YAxis
                  type="category" dataKey="name" width={90}
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-sec)', cursor: 'pointer' }}
                  tickLine={false} axisLine={false}
                />
                <Tooltip content={<ProductTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Bar dataKey="ok"    fill="var(--green)" fillOpacity={0.75} radius={[0, 3, 3, 0]} name="OK"       />
                <Bar dataKey="risco" fill="var(--red)"   fillOpacity={0.75} radius={[0, 3, 3, 0]} name="Em Risco" />
              </BarChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', gap: 16, marginTop: 8, justifyContent: 'flex-end' }}>
              {[['var(--green)', 'OK'], ['var(--red)', 'Em Risco']].map(([color, label]) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <div style={{ width: 8, height: 8, borderRadius: 2, background: color, opacity: 0.75 }} />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>{label}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Gauge */}
          <div style={{
            background: 'var(--surface1)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '18px 20px',
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          }}>
            <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)', marginBottom: 4 }}>
              Saúde da Infra
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 12 }}>
              horizonte {horizon}
            </div>
            <div style={{ position: 'relative', width: 180, height: 180 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={gaugeData}
                    cx="50%" cy="50%"
                    innerRadius={58} outerRadius={80}
                    startAngle={90} endAngle={-270}
                    dataKey="value"
                    strokeWidth={0}
                  >
                    <Cell fill={gaugeColor} fillOpacity={0.85} />
                    <Cell fill="var(--surface3)" fillOpacity={1} />
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div style={{
                position: 'absolute', inset: 0,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
              }}>
                <div style={{
                  fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700,
                  color: gaugeColor, lineHeight: 1,
                }}>
                  {healthPct}%
                </div>
                <div style={{ fontFamily: 'var(--font-sans)', fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                  operacional
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── SEÇÃO 5: Timeline ────────────────────────────────────────────── */}
        <div style={{
          background: 'var(--surface1)', border: '1px solid var(--border)',
          borderRadius: 8, overflow: 'hidden',
        }}>
          <div style={{
            padding: '14px 18px 10px',
            borderBottom: '1px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>
              Eventos Recentes
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)' }}>
              Servidores em risco elevado · últimas 24h
            </div>
          </div>
          {timelineEvents.map((s, idx) => (
            <div key={s.id} style={{
              display: 'flex', alignItems: 'center', gap: 16,
              padding: '10px 18px',
              borderBottom: idx < timelineEvents.length - 1 ? '1px solid var(--border)' : 'none',
              animation: `fadeInUp 0.3s ease ${idx * 50}ms both`,
            }}>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', flexShrink: 0, minWidth: 60 }}>
                {horasAtras(s, idx)}
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)', flexShrink: 0, minWidth: 160 }}>
                {s.product}
              </span>
              <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-pri)', flex: 1 }}>
                {ISSUE_PT[s.predictedIssue] ?? s.predictedIssue}
              </span>
              {severityBadge(s.failProb)}
            </div>
          ))}
        </div>

        {/* ── SEÇÃO 6: Tendência global ─────────────────────────────────────── */}
        <div style={{
          background: 'var(--surface1)', border: '1px solid var(--border)',
          borderRadius: 8, padding: '14px 20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <div>
              <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>
                Tendência Global · 24h
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                Média de failProb dos servidores monitorados
              </div>
            </div>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700,
              color: trendColor,
            }}>
              {trendLabel}
            </span>
          </div>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={trendData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
              <CartesianGrid stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="hour"
                tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
                tickLine={false} axisLine={{ stroke: 'var(--border)' }}
                interval={3}
              />
              <YAxis
                tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
                tickLine={false} axisLine={false}
                tickFormatter={v => `${v}%`}
              />
              <Tooltip content={<TrendTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
              <Line
                type="monotone" dataKey="avg"
                stroke={trendColor} strokeWidth={2} dot={false}
                activeDot={{ r: 3, fill: trendColor, stroke: 'var(--bg)', strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

      </main>
    </div>
  );
}
