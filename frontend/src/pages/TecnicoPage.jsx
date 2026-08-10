import { useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertTriangle, Clock3, Layers3, Users } from 'lucide-react';
import RiscoUnificado from '../components/RiscoUnificado';
import SemDados from '../components/SemDados';
import { grupos } from '../data/mockData';
import { useApi } from '../hooks/useApi';
import { useBreakpoint } from '../hooks/useBreakpoint';
import './DashboardPages.css';

const CLUSTER_COLORS = ['var(--teal)', 'var(--yellow)', 'var(--orange)', 'var(--purple)', 'var(--red)'];

function Module({ n, title, sub, children }) {
  return (
    <section className="dashboard-module">
      <header className="dashboard-module__header">
        <div>
          <span>MÓDULO {String(n).padStart(2, '0')}</span>
          <h2>{title}</h2>
          {sub && <p>{sub}</p>}
        </div>
      </header>
      <div className="dashboard-module__body">{children}</div>
    </section>
  );
}

function ClusterCard({ cluster, selected, onSelect }) {
  const color = CLUSTER_COLORS[cluster.id % CLUSTER_COLORS.length];
  const profile = cluster.perfil ?? {};
  const scores = [
    ['Temporalidade', cluster.score_T],
    ['Gravidade', cluster.score_G],
    ['Pressão OLA', cluster.score_V],
  ];

  return (
    <button
      type="button"
      className="cluster-card"
      aria-pressed={selected}
      onClick={onSelect}
      style={{ '--cluster-color': color }}
    >
      <div className="cluster-card__identity">
        <span>C{cluster.id}</span>
        <strong>{cluster.label}</strong>
        <small>{cluster.descricao}</small>
      </div>
      <div className="cluster-card__metrics">
        <div><strong>{cluster.tamanho.toLocaleString('pt-BR')}</strong><span>incidentes</span></div>
        <div><strong>{cluster.taxaViolacao.toFixed(3)}%</strong><span>violação OLA</span></div>
        <div><strong>{profile.pctP2?.toFixed(1) ?? '—'}%</strong><span>P2</span></div>
      </div>
      <div className="cluster-card__scores">
        {scores.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <i><b style={{ width: `${Math.min(100, (value ?? 0) * 10)}%` }} /></i>
            <strong>{value?.toFixed(1) ?? '—'}/10</strong>
          </div>
        ))}
      </div>
      <footer>
        <span><Clock3 size={13} /> hora média {profile.horaMedia ?? '—'}h</span>
        <span><Users size={13} /> {profile.grupo || 'grupo não identificado'}</span>
      </footer>
    </button>
  );
}

export default function TecnicoPage() {
  const { isMobile } = useBreakpoint();
  const [selectedCluster, setSelectedCluster] = useState(null);
  const { data: clusters, loading: clustersLoading, disponivel: clustersAvailable } = useApi('/clusters');
  const { disponivel: riskAvailable } = useApi('/risco');
  const rankedGroups = [...grupos].sort((left, right) => right.taxaViolacao - left.taxaViolacao);
  const clusterList = clustersAvailable ? clusters?.clusters ?? [] : [];
  const topCluster = clusterList.toSorted((left, right) => right.taxaViolacao - left.taxaViolacao)[0];

  return (
    <div className="dashboard-page">
      <header className="dashboard-page-header">
        <div>
          <h1>Investigação Técnica</h1>
          {!isMobile && <p>Equipes · triagem de risco · perfis operacionais</p>}
        </div>
      </header>

      <main className="dashboard-page__content">
        <section className="technical-brief">
          <div><AlertTriangle size={18} /></div>
          <section>
            <span>FOCO DA INVESTIGAÇÃO</span>
            <h2>{topCluster ? `${topCluster.label} concentra a maior taxa entre os clusters` : 'Aguardando perfis operacionais'}</h2>
            <p>Use os clusters como associação estatística e o XGBoost apenas para ordenar a triagem. Nenhum dos dois comprova causa raiz.</p>
          </section>
          <aside>
            <strong>{riskAvailable ? 'XGBOOST DISPONÍVEL' : 'RISCO INDISPONÍVEL'}</strong>
            <span>{clustersAvailable ? `K=${clusters?.k} · silhouette ${clusters?.silhouette?.toFixed(4)}` : 'clusters indisponíveis'}</span>
          </aside>
        </section>

        <Module n={1} title="Risco histórico por equipe" sub="Taxa real de violação OLA · use para selecionar onde investigar">
          <div style={{ width: '100%', minWidth: 0, minHeight: 330 }}>
            <ResponsiveContainer width="100%" height={330}>
              <BarChart data={rankedGroups} layout="vertical" margin={{ top: 0, right: 58, bottom: 0, left: 4 }} barSize={14}>
                <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 'dataMax + 1']} tickFormatter={(value) => `${value}%`} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} tickLine={false} axisLine={{ stroke: 'var(--border)' }} />
                <YAxis type="category" dataKey="id" width={58} tick={{ fontSize: 10, fill: 'var(--text-sec)' }} tickLine={false} axisLine={false} />
                <Tooltip
                  cursor={{ fill: 'rgba(255,255,255,.025)' }}
                  contentStyle={{ background: 'var(--surface3)', border: '1px solid var(--border-md)', borderRadius: 8, fontSize: 12 }}
                  formatter={(value) => [`${value}%`, 'Taxa real']}
                />
                <Bar dataKey="taxaViolacao" name="Taxa real" radius={[0, 4, 4, 0]}>
                  {rankedGroups.map((group) => (
                    <Cell key={group.id} fill={group.taxaViolacao > 3 ? 'var(--red)' : group.taxaViolacao > 1 ? 'var(--orange)' : 'var(--green)'} />
                  ))}
                  <LabelList dataKey="taxaViolacao" position="right" formatter={(value) => `${value}%`} style={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Module>

        <Module n={2} title="Triagem preditiva XGBoost" sub="Score não calibrado · SHAP global · conjunto de teste temporal histórico">
          <RiscoUnificado />
        </Module>

        <Module
          n={3}
          title="Perfis operacionais K-Means"
          sub={clustersAvailable
            ? `K=${clusters?.k} · silhouette ${clusters?.silhouette?.toFixed(4)} · ${clusters?.metricas?.total_incidentes?.toLocaleString('pt-BR')} incidentes`
            : 'Segmentação indisponível'}
        >
          {clustersLoading ? <div className="skeleton" style={{ height: 360 }} /> : !clustersAvailable ? (
            <SemDados mensagem="Modelo K-Means indisponível" />
          ) : (
            <>
              <div className="cluster-grid">
                {clusterList.map((cluster) => (
                  <ClusterCard
                    key={cluster.id}
                    cluster={cluster}
                    selected={selectedCluster === cluster.id}
                    onSelect={() => setSelectedCluster((current) => current === cluster.id ? null : cluster.id)}
                  />
                ))}
              </div>
              <div className="model-boundary-note">
                <Layers3 size={15} />
                <span>Os scores T/G/V usam escala de 0 a 10. Taxa de violação e participação P2 permanecem percentuais reais.</span>
              </div>
            </>
          )}
        </Module>
      </main>
    </div>
  );
}
