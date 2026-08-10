import { AlertTriangle, Gauge, ScanSearch } from 'lucide-react';
import { useApi } from '../hooks/useApi';
import SemDados from './SemDados';

const SHAP_LABELS = {
  grupo_viol_rate: 'Histórico de violação do grupo',
  rolling_30d: 'Volume médio em 30 dias',
  rolling_7d: 'Volume médio em 7 dias',
  aberto_por_enc: 'Origem da abertura',
  produto_freq: 'Frequência do produto',
  produto_enc: 'Produto',
  categoria_enc: 'Categoria',
  lag_7d: 'Volume há 7 dias',
  hora: 'Hora de abertura',
};

function validDistribution(distribution, total) {
  const entries = Object.values(distribution ?? {});
  if (!entries.length || !total) return false;
  const countSum = entries.reduce((sum, item) => sum + (item.count ?? 0), 0);
  const pctSum = entries.reduce((sum, item) => sum + (item.pct ?? 0), 0);
  const ordered = entries.every((item) => (
    item.limite_inferior == null
    || item.limite_superior == null
    || item.limite_inferior <= item.limite_superior
  ));
  return countSum === total && Math.abs(pctSum - 100) <= 0.2 && ordered;
}

function bandLabel(name, item) {
  const from = ((item?.limite_inferior ?? 0) * 100).toFixed(1);
  const to = ((item?.limite_superior ?? 1) * 100).toFixed(1);
  return `${name.toUpperCase()} · score ${from}–${to}`;
}

export default function RiscoUnificado() {
  const { data, loading, disponivel } = useApi('/risco');

  if (loading) return <div className="skeleton" style={{ height: 300 }} />;
  if (!disponivel) return <SemDados mensagem="Modelo XGBoost indisponível" />;

  const priorities = data?.risco_por_prioridade ?? {};
  const distribution = data?.distribuicao_risco ?? {};
  const metrics = data?.metricas ?? {};
  const shap = (data?.feature_importance_shap ?? []).slice(0, 5);
  const maxShap = shap[0]?.shap_mean_abs || 1;
  const distributionIsValid = validDistribution(distribution, metrics.total_teste);

  return (
    <div className="risk-analysis">
      <div className="risk-analysis__notice">
        <Gauge size={15} />
        <span>O valor exibido é um <strong>score de ordenação</strong>, não a probabilidade real de violação.</span>
      </div>

      <div className="risk-analysis__grid">
        <section>
          <header><ScanSearch size={15} /> Score por prioridade</header>
          <div className="risk-priorities">
            {['P2', 'P3'].map((priority) => {
              const item = priorities[priority] ?? {};
              return (
                <article key={priority} style={{ '--risk-color': priority === 'P2' ? 'var(--teal)' : 'var(--yellow)' }}>
                  <span>{priority}</span>
                  <strong>{((item.media_prob ?? 0) * 100).toFixed(2)}</strong>
                  <small>score médio / 100</small>
                  <footer>
                    <span>{item.taxa_violacao_real ?? '—'}% taxa real</span>
                    <span>{item.pct_alto_risco ?? '—'}% acima do corte</span>
                  </footer>
                </article>
              );
            })}
          </div>
          <p className="risk-analysis__inference">
            P3 apresenta score médio e taxa real maiores neste teste. A hipótese de gargalo por priorização de P2 ainda precisa ser testada com fila, escala e tempo de atendimento.
          </p>
        </section>

        <section>
          <header>Distribuição da triagem</header>
          {!distributionIsValid ? (
            <div className="risk-analysis__invalid" role="status">
              <AlertTriangle size={17} />
              <div>
                <strong>Distribuição ocultada</strong>
                <span>O artefato atual possui faixas sobrepostas. As métricas principais continuam válidas; regenere o XGBoost para exibir as bandas.</span>
              </div>
            </div>
          ) : (
            <div className="risk-bands">
              {['alto', 'medio', 'baixo'].map((name) => {
                const item = distribution[name] ?? {};
                const color = name === 'alto' ? 'var(--red)' : name === 'medio' ? 'var(--orange)' : 'var(--green)';
                return (
                  <div key={name} style={{ '--band-color': color }}>
                    <span>{bandLabel(name, item)}</span>
                    <strong>{item.count?.toLocaleString('pt-BR')} · {item.pct}%</strong>
                    <i><b style={{ width: `${item.pct ?? 0}%` }} /></i>
                    <small>{item.violacoes_reais} violações reais</small>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section>
          <header>Vetores globais SHAP</header>
          <div className="shap-list">
            {shap.map((feature) => {
              const relative = feature.shap_mean_abs / maxShap * 100;
              return (
                <div key={feature.feature}>
                  <span>{SHAP_LABELS[feature.feature] ?? feature.feature}</span>
                  <strong>{feature.shap_mean_abs.toFixed(3)}</strong>
                  <i><b style={{ width: `${relative}%` }} /></i>
                </div>
              );
            })}
          </div>
          <p className="risk-analysis__footnote">SHAP mostra contribuição média global para o score; não comprova causalidade.</p>
        </section>
      </div>

      <div className="risk-analysis__metrics">
        <span>Recall <strong>{((metrics.recall_violacao ?? 0) * 100).toFixed(1)}%</strong></span>
        <span>Precisão <strong>{((metrics.precision_violacao ?? 0) * 100).toFixed(1)}%</strong></span>
        <span>PR-AUC <strong>{metrics.pr_auc?.toFixed(4) ?? '—'}</strong></span>
        <span>Teste <strong>{metrics.total_teste?.toLocaleString('pt-BR') ?? '—'} casos</strong></span>
      </div>
    </div>
  );
}
