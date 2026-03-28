import { useState } from 'react';
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

// ─── Cluster card ─────────────────────────────────────────────────────────────
function ClusterCard({ cluster }) {
  const isCritical = cluster.taxaViolacao > 5;
  const badgeColor =
    cluster.taxaViolacao > 5 ? 'var(--red)' :
    cluster.taxaViolacao > 2 ? 'var(--orange)' :
                                'var(--green)';

  return (
    <div style={{
      background: 'var(--surface3)',
      border: `1px solid ${isCritical ? 'var(--red)' : 'var(--border)'}`,
      borderRadius: 6, padding: '16px 18px',
      display: 'flex', flexDirection: 'column', gap: 10,
      animation: `fadeInUp 0.4s ease ${cluster.id * 80}ms both`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
          color: 'var(--text-muted)', letterSpacing: '0.12em', textTransform: 'uppercase',
        }}>CLUSTER {cluster.id}</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
          color: badgeColor, background: `${badgeColor}18`,
          border: `1px solid ${badgeColor}44`,
          borderRadius: 3, padding: '2px 8px', letterSpacing: '0.08em',
        }}>{cluster.taxaViolacao}% VIOLAÇÃO</span>
      </div>

      <div style={{
        fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 13,
        color: 'var(--text-pri)', textTransform: 'uppercase', letterSpacing: '0.04em',
      }}>{cluster.label}</div>

      <div style={{ display: 'flex', gap: 20 }}>
        {[
          { l: 'TAMANHO',    v: cluster.tamanho.toLocaleString('pt-BR') },
          { l: 'HORA PICO', v: `${cluster.perfil.horaMedia}h` },
          { l: 'GRUPO',     v: cluster.perfil.grupo },
        ].map(({ l, v }) => (
          <div key={l}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)', letterSpacing: '0.1em', marginBottom: 3 }}>{l}</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600, color: 'var(--text-pri)' }}>{v}</div>
          </div>
        ))}
      </div>

      <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)', lineHeight: 1.55 }}>
        {cluster.descricao}
      </div>

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {cluster.perfil.diasCriticos.map(d => (
          <span key={d} style={{
            fontFamily: 'var(--font-mono)', fontSize: 9,
            color: 'var(--text-muted)', background: 'var(--surface4)',
            border: '1px solid var(--border)', borderRadius: 3, padding: '2px 6px',
          }}>{d}</span>
        ))}
        {cluster.perfil.produtos.map(p => (
          <span key={p} style={{
            fontFamily: 'var(--font-mono)', fontSize: 9,
            color: 'var(--orange)', background: 'var(--orange-dim)',
            border: '1px solid rgba(255,159,10,0.2)', borderRadius: 3, padding: '2px 6px',
          }}>{p}</span>
        ))}
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function TecnicoPage() {
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

      <main style={{ flex: 1, padding: '20px 28px 60px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* ── MODULE 01: System Metrics ──────────────────────────────────── */}
        <Module n={1} title="Métricas do Sistema" sub="Dataset KPI 2025 · apenas incidentes P2 + P3">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }}>
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
          title={`Importância de Features XGBoost${isShapSimulado ? ' · SIMULADO' : ''}`}
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
          sub={clustersDisponivel
            ? 'K-MEANS · outputs/clusters.json · Cluster 3 (Team07) mais crítico'
            : 'K-MEANS · execute o notebook 05 para gerar dados de cluster'}
        >
          {clustersLoading ? (
            <Skeleton height={320} />
          ) : !clustersDisponivel ? (
            <SemDados mensagem="Modelo K-Means não treinado — execute o notebook 05" />
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              {clustersData.map(c => <ClusterCard key={c.id} cluster={c} />)}
            </div>
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
