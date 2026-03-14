import { useNavigate } from 'react-router-dom';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, PieChart, Pie, Cell,
  ReferenceLine,
} from 'recharts';
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle } from 'lucide-react';
import {
  volumeMensal2025, produtos, kpiAtingimento,
  previsaoVolume, violacoesReais2025, olaTargets,
} from '../data/mockData';

// ─── Shared tooltip ───────────────────────────────────────────────────────────
function ChartTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 6, padding: '8px 12px',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 6 }}>
        {label}
      </div>
      {payload.map((p, i) => (
        <div key={i} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: p.color || p.fill, marginBottom: 2 }}>
          {p.name}: {formatter ? formatter(p.value) : p.value}
        </div>
      ))}
    </div>
  );
}

// ─── KPI card ─────────────────────────────────────────────────────────────────
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

// ─── Section heading ──────────────────────────────────────────────────────────
function SectionHead({ title, sub }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>
        {title}
      </div>
      {sub && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)', marginTop: 3 }}>
          {sub}
        </div>
      )}
    </div>
  );
}

// ─── Chart card wrapper ───────────────────────────────────────────────────────
function ChartCard({ children, style }) {
  return (
    <div style={{
      background: 'var(--surface1)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '18px 20px',
      ...style,
    }}>
      {children}
    </div>
  );
}

// ─── Gauge donut ──────────────────────────────────────────────────────────────
function Gauge({ label, pct, color, sub }) {
  const capped = Math.min(pct, 100);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
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
              <Cell fill={color} fillOpacity={0.85} />
              <Cell fill="var(--surface3)" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 26, fontWeight: 700,
            color, lineHeight: 1,
          }}>{pct}%</div>
          <div style={{ fontFamily: 'var(--font-sans)', fontSize: 9, color: 'var(--text-sec)', marginTop: 3 }}>
            atingimento
          </div>
        </div>
      </div>
      <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 12, color: 'var(--text-pri)' }}>
        {label}
      </div>
      {sub && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-sec)', textAlign: 'center' }}>
          {sub}
        </div>
      )}
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', textAlign: 'center' }}>
        baseado em previsão Prophet
      </div>
    </div>
  );
}

export default function GestaoPage() {
  const navigate = useNavigate();
  const p2 = kpiAtingimento.P2;
  const p3 = kpiAtingimento.P3;
  const p2Crítico = violacoesReais2025.P2 > olaTargets.P2.metaViolacoesAno.max;

  // Top 8 produtos para o gráfico horizontal
  const produtosTop8 = [...produtos].slice(0, 8);

  return (
    <main style={{
      flex: 1, padding: '20px 24px 40px',
      display: 'flex', flexDirection: 'column', gap: 16,
      maxWidth: 1600, width: '100%', margin: '0 auto',
    }}>

      {/* ── SEÇÃO 1: Banner de status KPI ─────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>

        {/* P2 — crítico */}
        <div style={{
          background: 'var(--red-dim)', border: '1px solid var(--red)',
          borderRadius: 8, padding: '20px 24px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          animation: 'fadeInUp 0.3s ease both',
        }}>
          <div>
            <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 13, color: 'var(--text-sec)', marginBottom: 6 }}>
              KPI P2 — Alta Prioridade
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 36, fontWeight: 700, color: 'var(--red)', lineHeight: 1 }}>
              42 violações
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
              Meta: 36–39 violações · ano 2025
            </div>
          </div>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
            color: 'var(--red)', background: 'var(--red-dim)', border: '1px solid var(--red)',
            borderRadius: 4, padding: '4px 10px', letterSpacing: '0.1em',
          }}>ACIMA DA META</span>
        </div>

        {/* P3 — ok */}
        <div style={{
          background: 'rgba(0,230,118,0.06)', border: '1px solid var(--green)',
          borderRadius: 8, padding: '20px 24px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          animation: 'fadeInUp 0.35s ease both',
        }}>
          <div>
            <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 13, color: 'var(--text-sec)', marginBottom: 6 }}>
              KPI P3 — Média Prioridade
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 36, fontWeight: 700, color: 'var(--green)', lineHeight: 1 }}>
              196 violações
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
              Meta: 231–263 violações · ano 2025
            </div>
          </div>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
            color: 'var(--green)', background: 'rgba(0,230,118,0.10)', border: '1px solid var(--green)',
            borderRadius: 4, padding: '4px 10px', letterSpacing: '0.1em',
          }}>DENTRO DA META</span>
        </div>
      </div>

      {/* ── SEÇÃO 2: 4 KPI Cards ──────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <KpiCard
          label="Previsão D+1"
          value={`${previsaoVolume.D1.total}`}
          sub={`P2: ${previsaoVolume.D1.P2} · P3: ${previsaoVolume.D1.P3} incidentes`}
          color="var(--orange)"
          Icon={AlertTriangle}
          delay={0}
        />
        <KpiCard
          label="Previsão D+7"
          value={`${previsaoVolume.D7.total}`}
          sub="incidentes · próxima semana"
          color="var(--yellow)"
          Icon={TrendingUp}
          delay={50}
        />
        <KpiCard
          label="Atingimento P2"
          value={`${p2.pctAtingimento}%`}
          sub={`projeção: ${p2.previsaoFechamento} violações`}
          color="var(--red)"
          Icon={TrendingDown}
          delay={100}
        />
        <KpiCard
          label="Atingimento P3"
          value={`${p3.pctAtingimento}%`}
          sub={`projeção: ${p3.previsaoFechamento} violações`}
          color="var(--green)"
          Icon={CheckCircle}
          delay={150}
        />
      </div>

      {/* ── SEÇÃO 3: Violações mensais 2025 ───────────────────────────────── */}
      <ChartCard>
        <SectionHead
          title="Violações de OLA por mês — 2025"
          sub="P2 (≤4h) e P3 (≤12h) · linha de referência = meta mensal P2"
        />
        <ResponsiveContainer width="100%" height={220}>
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
              content={<ChartTooltip />}
              cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            />
            <ReferenceLine
              y={3.25}
              stroke="var(--red)"
              strokeDasharray="4 4"
              strokeOpacity={0.5}
              label={{ value: 'meta P2/mês', position: 'right', fill: 'var(--red)', fontSize: 9, fontFamily: 'var(--font-mono)' }}
            />
            <Bar dataKey="violP2" name="P2 violações" fill="var(--red)"    fillOpacity={0.8} radius={[2,2,0,0]} />
            <Bar dataKey="violP3" name="P3 violações" fill="var(--orange)" fillOpacity={0.8} radius={[2,2,0,0]} />
          </BarChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', gap: 16, marginTop: 8, justifyContent: 'flex-end' }}>
          {[['var(--red)', 'P2 violações'], ['var(--orange)', 'P3 violações']].map(([c, l]) => (
            <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: c, opacity: 0.8 }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>{l}</span>
            </div>
          ))}
        </div>
      </ChartCard>

      {/* ── SEÇÃO 4: Volume total por produto (horizontal) ────────────────── */}
      <ChartCard>
        <SectionHead
          title="Volume e Violações por Produto"
          sub="Clique na barra para ver detalhes em Monitoramento"
        />
        <ResponsiveContainer width="100%" height={240}>
          <BarChart
            data={produtosTop8}
            layout="vertical"
            margin={{ top: 4, right: 16, bottom: 4, left: 20 }}
            barSize={10}
            onClick={d => { if (d?.activeLabel) navigate('/monitoramento'); }}
            style={{ cursor: 'pointer' }}
          >
            <XAxis
              type="number"
              tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
              tickLine={false} axisLine={{ stroke: 'var(--border)' }}
            />
            <YAxis
              type="category" dataKey="id" width={40}
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
                    borderRadius: 6, padding: '8px 12px',
                  }}>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: '#60a5fa', marginBottom: 2 }}>total: {d?.total}</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--red)' }}>violações: {d?.violacoes} ({d?.taxaViolacao}%)</div>
                  </div>
                );
              }}
              cursor={{ fill: 'rgba(255,255,255,0.03)' }}
            />
            <Bar dataKey="total"    name="Total"     fill="#60a5fa" fillOpacity={0.7} radius={[0,3,3,0]} />
            <Bar dataKey="violacoes" name="Violações" fill="var(--red)" fillOpacity={0.8} radius={[0,3,3,0]} />
          </BarChart>
        </ResponsiveContainer>
        <div style={{ display: 'flex', gap: 16, marginTop: 8, justifyContent: 'flex-end' }}>
          {[['#60a5fa', 'Total'], ['var(--red)', 'Violações']].map(([c, l]) => (
            <div key={l} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: c, opacity: 0.8 }} />
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>{l}</span>
            </div>
          ))}
        </div>
      </ChartCard>

      {/* ── SEÇÃO 5: Tendência de volume mensal ──────────────────────────── */}
      <ChartCard>
        <SectionHead
          title="Evolução mensal de incidentes KPI — 2025"
          sub="P2 e P3 · apenas incidentes Alta e Média prioridade"
        />
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={volumeMensal2025} margin={{ top: 8, right: 16, bottom: 0, left: -10 }}>
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
            <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.08)', strokeWidth: 1 }} />
            <Line type="monotone" dataKey="P2" name="P2" stroke="var(--red)"    strokeWidth={2} dot={{ r: 3, fill: 'var(--red)', stroke: 'var(--bg)', strokeWidth: 2 }} />
            <Line type="monotone" dataKey="P3" name="P3" stroke="var(--orange)" strokeWidth={2} dot={{ r: 3, fill: 'var(--orange)', stroke: 'var(--bg)', strokeWidth: 2 }} />
          </LineChart>
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

      {/* ── SEÇÃO 6: Projeção de atingimento ─────────────────────────────── */}
      <ChartCard>
        <SectionHead
          title="Projeção de atingimento — baseado no Prophet"
          sub="Estimativa de fechamento de ano com base na série histórica · não confundir com os valores reais do topo"
        />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 64, padding: '8px 0' }}>
          <Gauge
            label="KPI P2"
            pct={p2.pctAtingimento}
            color="var(--red)"
            sub={`Projeção: ${p2.previsaoFechamento} violações`}
          />
          <Gauge
            label="KPI P3"
            pct={p3.pctAtingimento}
            color="var(--green)"
            sub={`Projeção: ${p3.previsaoFechamento} violações`}
          />
        </div>
        <div style={{
          textAlign: 'center', marginTop: 12,
          fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)',
        }}>
          Projeção de fechamento: P2 = {p2.previsaoFechamento} violações · P3 = {p3.previsaoFechamento} violações
        </div>
      </ChartCard>

    </main>
  );
}
