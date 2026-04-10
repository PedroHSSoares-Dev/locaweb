import { useApi } from '../hooks/useApi';
import SemDados from './SemDados';

function Skeleton({ height = 80 }) {
  return <div className="skeleton" style={{ height }} />;
}

const SHAP_LABELS = {
  prioridade_bin:   'Prioridade (P2 vs P3)',
  grupo_freq:       'Freq. Histórica Grupo',
  subcategoria_enc: 'Subcategoria',
  aberto_por_enc:   'Usuário',
  produto_freq:     'Freq. Histórica Produto',
  rolling_7d:       'Volume Médio 7 dias',
  categoria_enc:    'Categoria',
  grupo_enc:        'Grupo Designado',
  produto_enc:      'Produto',
  hora:             'Hora de Abertura',
};

export default function RiscoUnificado() {
  const { data, loading, disponivel } = useApi('/risco');

  if (loading) return <Skeleton height={280} />;
  if (!disponivel) return <SemDados mensagem="Modelo XGBoost não treinado — execute o notebook 04" />;

  const prio    = data?.risco_por_prioridade ?? {};
  const dist    = data?.distribuicao_risco ?? {};
  const shap    = (data?.feature_importance_shap ?? []).slice(0, 5);
  const m       = data?.metricas ?? {};
  const maxShap = shap[0]?.shap_mean_abs ?? 1;

  const P3 = prio['P3'] ?? {};
  const P2 = prio['P2'] ?? {};

  const DIST_CONFIG = {
    alto:  { label: 'ALTO (>0.55)',      cor: 'var(--red)'    },
    medio: { label: 'MÉDIO (0.20–0.55)', cor: 'var(--orange)' },
    baixo: { label: 'BAIXO (<0.20)',     cor: 'var(--green)'  },
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>

      {/* ── Título interno ─────────────────────────────────────────────── */}
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 9,
        color: 'var(--green)', letterSpacing: '0.14em',
        marginBottom: 16,
      }}>■ ANÁLISE PREDITIVA DE VIOLAÇÃO (XGBOOST_V4)</div>

      {/* ── 3 colunas ──────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '30% 40% 30%', gap: 20, minHeight: 220 }}>

        {/* Coluna 1 — Âncoras de risco */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 8,
            color: 'var(--text-muted)', letterSpacing: '0.14em', marginBottom: 4,
          }}>ÂNCORAS DE RISCO</div>

          {[
            { id: 'P3', d: P3, cor: '#ffcc00', status: 'RISCO MÉDIO'   },
            { id: 'P2', d: P2, cor: '#5ac8fa', status: 'RISCO NOMINAL' },
          ].map(({ id, d, cor, status }) => (
            <div key={id} style={{
              borderLeft: `3px solid ${cor}`,
              paddingLeft: 12,
              paddingBottom: 8,
              borderBottom: '1px solid var(--border)',
            }}>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 9,
                color: 'var(--text-muted)', marginBottom: 2,
              }}>PRIORITY_{id}</div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 28,
                fontWeight: 700, color: cor, lineHeight: 1,
              }}>
                {((d.media_prob ?? 0) * 100).toFixed(1)}%
              </div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 8,
                color: cor, fontWeight: 700, marginTop: 2, marginBottom: 4,
              }}>{status}</div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 9,
                color: 'var(--text-muted)',
              }}>{(d.n_incidentes ?? 0).toLocaleString('pt-BR')} incidentes</div>
            </div>
          ))}

          {/* Insight box */}
          <div style={{
            background: 'var(--surface3)',
            border: '1px solid var(--border)',
            borderRadius: 4, padding: '10px 12px',
            fontFamily: 'var(--font-mono)', fontSize: 9,
            color: 'var(--text-sec)', lineHeight: 1.6,
            marginTop: 4,
          }}>
            <span style={{ color: 'var(--orange)', fontWeight: 700 }}>INSIGHT: </span>
            P3 viola {(P3.taxa_violacao_real / (P2.taxa_violacao_real || 1)).toFixed(0)}× mais que P2
            ({P3.taxa_violacao_real}% vs {P2.taxa_violacao_real}%).
            A priorização manual de P2 gera gargalo em P3.
          </div>
        </div>

        {/* Coluna 2 — Distribuição de alertas */}
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 8,
            color: 'var(--text-muted)', letterSpacing: '0.14em', marginBottom: 12,
          }}>DISTRIBUIÇÃO DE ALERTAS</div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {['alto', 'medio', 'baixo'].map(cat => {
              const d   = dist[cat] ?? {};
              const cfg = DIST_CONFIG[cat];
              return (
                <div key={cat}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 9,
                      color: cfg.cor, fontWeight: 700,
                    }}>{cfg.label}</span>
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 9,
                      color: 'var(--text-muted)',
                    }}>
                      {(d.count ?? 0).toLocaleString('pt-BR')} inc ({d.pct ?? 0}%)
                    </span>
                  </div>
                  <div style={{ height: 8, background: 'var(--surface4)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%',
                      width: `${d.pct ?? 0}%`,
                      background: cfg.cor,
                      borderRadius: 2,
                      opacity: 0.85,
                    }} />
                  </div>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: 8,
                    color: 'var(--text-muted)', marginTop: 3,
                  }}>{d.violacoes_reais ?? 0} violações reais neste grupo</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Coluna 3 — Vetores de risco SHAP */}
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 8,
            color: 'var(--text-muted)', letterSpacing: '0.14em', marginBottom: 12,
          }}>VETORES DE RISCO (SHAP_VALUES)</div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {shap.map(f => {
              const pct = ((f.shap_mean_abs / maxShap) * 100).toFixed(0);
              return (
                <div key={f.feature}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 9,
                      color: 'var(--text-sec)', textTransform: 'uppercase',
                    }}>{SHAP_LABELS[f.feature] ?? f.feature}</span>
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 9,
                      color: '#5ac8fa', fontWeight: 700,
                    }}>{pct}%</span>
                  </div>
                  <div style={{ height: 5, background: 'var(--surface4)', borderRadius: 2 }}>
                    <div style={{
                      width: `${pct}%`, height: '100%',
                      background: '#5ac8fa', borderRadius: 2, opacity: 0.8,
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Rodapé — métricas do modelo ────────────────────────────────── */}
      <div style={{
        marginTop: 16,
        paddingTop: 10,
        borderTop: '1px solid var(--green)33',
        fontFamily: 'var(--font-mono)', fontSize: 9,
        color: 'var(--green)', letterSpacing: '0.08em',
      }}>
        METRICS: ROC-AUC: {m.roc_auc ?? '—'} | PR-AUC: {m.pr_auc ?? '—'} | RECALL: {m.recall_violacao ? `${(m.recall_violacao * 100).toFixed(1)}%` : '—'} | F1-SCORE: {m.f1_violacao ?? '—'} | THRESHOLD: {data?.threshold_otimizado ?? '—'}
      </div>

    </div>
  );
}
