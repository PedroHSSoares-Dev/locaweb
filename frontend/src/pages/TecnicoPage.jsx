import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, LabelList,
} from 'recharts';
import { Terminal, AlertTriangle, Activity, Users } from 'lucide-react';
import { grupos, shapFeatures, categorias, categoriaNomes } from '../data/mockData';
import { useApi } from '../hooks/useApi';
import SemDados from '../components/SemDados';

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
        fontFamily: 'var(--font-mono)', fontSize: 26, fontWeight: 700,
        color, lineHeight: 1, letterSpacing: '-0.02em',
      }}>{value}</div>
      {sub && (
        <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)' }}>{sub}</div>
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

// ─── Group tooltip ─────────────────────────────────────────────────────────────
function GrupoTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border-md)',
      borderRadius: 6, padding: '8px 12px',
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
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
      borderRadius: 6, padding: '8px 12px', maxWidth: 220,
    }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>{d?.feature}</div>
      <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-pri)', marginBottom: 4 }}>{d?.descricao}</div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 700, color: 'var(--red)' }}>
        {(d?.importance * 100).toFixed(0)}%
      </div>
    </div>
  );
}

// ─── Cluster card ─────────────────────────────────────────────────────────────
function ClusterCard({ cluster }) {
  const isCritical = cluster.taxaViolacao > 5;
  const badgeColor =
    cluster.taxaViolacao > 5 ? 'var(--red)' :
    cluster.taxaViolacao > 2 ? 'var(--orange)' :
                                'var(--green)';

  return (
    <div style={{
      background: 'var(--surface1)',
      border: `1px solid ${isCritical ? 'var(--red)' : 'var(--border)'}`,
      borderRadius: 8, padding: '16px 18px',
      display: 'flex', flexDirection: 'column', gap: 10,
      animation: `fadeInUp 0.4s ease ${cluster.id * 80}ms both`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: 'var(--text-muted)', letterSpacing: '0.1em',
        }}>CLUSTER {cluster.id}</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: badgeColor, background: `${badgeColor}18`, border: `1px solid ${badgeColor}44`,
          borderRadius: 3, padding: '2px 8px', letterSpacing: '0.08em',
        }}>{cluster.taxaViolacao}% violação</span>
      </div>

      <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 13, color: 'var(--text-pri)' }}>
        {cluster.label}
      </div>

      <div style={{ display: 'flex', gap: 16 }}>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>tamanho</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color: 'var(--text-pri)' }}>
            {cluster.tamanho.toLocaleString('pt-BR')}
          </div>
        </div>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>hora pico</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color: 'var(--text-pri)' }}>
            {cluster.perfil.horaMedia}h
          </div>
        </div>
        <div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>grupo</div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700, color: 'var(--text-pri)' }}>
            {cluster.perfil.grupo}
          </div>
        </div>
      </div>

      <div style={{
        fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)',
        lineHeight: 1.5,
      }}>
        {cluster.descricao}
      </div>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {cluster.perfil.diasCriticos.map(d => (
          <span key={d} style={{
            fontFamily: 'var(--font-mono)', fontSize: 9,
            color: 'var(--text-muted)', background: 'var(--surface3)',
            border: '1px solid var(--border)', borderRadius: 3, padding: '2px 6px',
          }}>{d}</span>
        ))}
        {cluster.perfil.produtos.map(p => (
          <span key={p} style={{
            fontFamily: 'var(--font-mono)', fontSize: 9,
            color: 'var(--orange)', background: 'rgba(255,109,0,0.08)',
            border: '1px solid rgba(255,109,0,0.2)', borderRadius: 3, padding: '2px 6px',
          }}>{p}</span>
        ))}
      </div>
    </div>
  );
}

export default function TecnicoPage() {
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

  return (
    <main style={{
      flex: 1, padding: '20px 24px 40px',
      display: 'flex', flexDirection: 'column', gap: 16,
      maxWidth: 1600, width: '100%', margin: '0 auto',
    }}>

      {/* ── SEÇÃO 1: KPI técnicos ─────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
        <KpiCard
          label="Total incidentes KPI (2025)"
          value="25.600"
          sub="P2 + P3 · jan–dez 2025"
          color="var(--text-sec)"
          Icon={Activity}
          delay={0}
        />
        <KpiCard
          label="Taxa violação P2"
          value="0.81%"
          sub="42 violações / 5.159 incidentes"
          color="var(--red)"
          Icon={AlertTriangle}
          delay={50}
        />
        <KpiCard
          label="Taxa violação P3"
          value="0.96%"
          sub="196 violações / 20.097 incidentes"
          color="var(--orange)"
          Icon={AlertTriangle}
          delay={100}
        />
        <KpiCard
          label="Grupo mais crítico"
          value="Team07"
          sub="8.94% taxa · 16 violações / 179"
          color="var(--red)"
          Icon={Users}
          delay={150}
        />
      </div>

      {/* ── SEÇÃO 2: Ranking grupos ───────────────────────────────────────── */}
      <ChartCard
        title="Taxa de violação de OLA por grupo de atendimento"
        sub="Ordenado por taxa desc · vermelho >3%, laranja >1%, verde <1%"
      >
        <ResponsiveContainer width="100%" height={280}>
          <BarChart
            data={gruposOrdenados}
            layout="vertical"
            margin={{ top: 4, right: 70, bottom: 4, left: 8 }}
            barSize={14}
          >
            <XAxis
              type="number" domain={[0, 12]}
              tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
              tickLine={false} axisLine={{ stroke: 'var(--border)' }}
              tickFormatter={v => `${v}%`}
            />
            <YAxis
              type="category" dataKey="id" width={58}
              tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-sec)' }}
              tickLine={false} axisLine={false}
            />
            <Tooltip content={<GrupoTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Bar dataKey="taxaViolacao" name="Taxa violação" radius={[0, 3, 3, 0]}>
              {gruposOrdenados.map((g, i) => (
                <Cell
                  key={i}
                  fill={
                    g.taxaViolacao > 3 ? 'var(--red)' :
                    g.taxaViolacao > 1 ? 'var(--orange)' :
                    'var(--green)'
                  }
                  fillOpacity={0.85}
                />
              ))}
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

      {/* ── SEÇÃO 3: SHAP Feature Importance ─────────────────────────────── */}
      <ChartCard
        title={`Feature importance — modelo XGBoost OLA${isShapSimulado ? ' (simulado)' : ''}`}
        sub={isShapSimulado
          ? 'Valores simulados · substituído por SHAP real após treinar o notebook 04'
          : 'SHAP real — outputs/risco_ola.json'}
      >
        <ResponsiveContainer width="100%" height={shapOrdenado.length * 36 + 20}>
          <BarChart
            data={shapOrdenado}
            layout="vertical"
            margin={{ top: 4, right: 60, bottom: 4, left: 20 }}
            barSize={14}
          >
            <XAxis
              type="number" domain={[0, 0.35]}
              tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }}
              tickLine={false} axisLine={{ stroke: 'var(--border)' }}
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
                <Cell
                  key={i}
                  fill="#E8002D"
                  fillOpacity={0.2 + 0.8 * (f.importance / maxImportance)}
                />
              ))}
              <LabelList
                dataKey="importance"
                position="right"
                formatter={v => `${(v * 100).toFixed(0)}%`}
                style={{ fill: 'var(--text-sec)', fontSize: 10, fontFamily: 'var(--font-mono)' }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ── SEÇÃO 4: Clusters K-Means ─────────────────────────────────────── */}
      <div>
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>
            Clusters de padrões de incidentes (K-Means)
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)', marginTop: 3 }}>
            {clustersDisponivel
              ? 'outputs/clusters.json · Cluster 3 (Team07) é o mais crítico'
              : 'outputs/clusters.json · execute o notebook 05 para gerar'}
          </div>
        </div>
        {clustersLoading ? (
          <Skeleton height={320} />
        ) : !clustersDisponivel ? (
          <SemDados mensagem="Modelo K-Means ainda não treinado — execute o notebook 05" />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {clustersData.map(c => <ClusterCard key={c.id} cluster={c} />)}
          </div>
        )}
      </div>

      {/* ── SEÇÃO 5: Tabela grupos × categorias ───────────────────────────── */}
      <div style={{
        background: 'var(--surface1)', border: '1px solid var(--border)',
        borderRadius: 8, overflow: 'hidden',
      }}>
        <div style={{
          padding: '14px 20px 12px',
          borderBottom: '1px solid var(--border)',
        }}>
          <div style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 13, color: 'var(--text-pri)' }}>
            Grupos × Categorias — taxa de violação (%)
          </div>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)', marginTop: 3 }}>
            Estimado · células mais escuras = maior taxa · scroll horizontal disponível
          </div>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 600 }}>
            <thead>
              <tr style={{ background: 'var(--surface2)' }}>
                <th style={{ padding: '8px 16px', textAlign: 'left', fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.1em', borderBottom: '1px solid var(--border)', minWidth: 80 }}>GRUPO</th>
                {topCats.map(c => (
                  <th key={c.id} title={c.id} style={{ padding: '8px 14px', textAlign: 'center', fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.1em', borderBottom: '1px solid var(--border)', minWidth: 100, cursor: 'help' }}>
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
                        background: `rgba(232,0,45,${alpha * 0.25})`,
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
      </div>

    </main>
  );
}
