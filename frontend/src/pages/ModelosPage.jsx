import { useBreakpoint } from '../hooks/useBreakpoint';
import { useApi } from '../hooks/useApi';
import SemDados from '../components/SemDados';

function Skeleton({ height = 80 }) {
  return <div className="skeleton" style={{ height }} />;
}

function PageHeader({ title, sub }) {
  const { isMobile } = useBreakpoint();
  return (
    <div style={{
      padding: isMobile ? '12px 16px 12px 56px' : '16px 28px',
      borderBottom: '1px solid var(--border)',
      background: 'var(--surface1)',
      flexShrink: 0, position: 'sticky', top: 0, zIndex: 10,
    }}>
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
  );
}

function Module({ n, title, sub, children }) {
  return (
    <div style={{
      background: 'var(--surface2)', border: '1px solid var(--border)',
      borderRadius: 6, overflow: 'hidden',
    }}>
      <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)' }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)',
          letterSpacing: '0.16em', marginBottom: 3,
        }}>MODULE {String(n).padStart(2, '0')}</div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 14, fontWeight: 600,
          color: 'var(--text-pri)', textTransform: 'uppercase', letterSpacing: '0.04em',
        }}>{title}</div>
        {sub && (
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-sec)', marginTop: 3 }}>
            {sub}
          </div>
        )}
      </div>
      <div style={{ padding: '20px 24px 24px' }}>{children}</div>
    </div>
  );
}

// Cartão de métrica com explicação integrada
function MetricCard({ label, value, sub, color = 'var(--teal)', badge, explain, context }) {
  return (
    <div style={{
      background: 'var(--surface3)', border: '1px solid var(--border)',
      borderTop: `2px solid ${color}`, borderRadius: 6, padding: '16px 18px',
      display: 'flex', flexDirection: 'column', gap: 0,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
          color: 'var(--text-muted)', letterSpacing: '0.14em', textTransform: 'uppercase',
        }}>{label}</div>
        {badge && (
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 700,
            color: badge.color, background: `${badge.color}18`,
            border: `1px solid ${badge.color}44`,
            borderRadius: 3, padding: '2px 6px', letterSpacing: '0.1em',
          }}>{badge.text}</span>
        )}
      </div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 400,
        color, lineHeight: 1, marginBottom: sub ? 4 : 0,
      }}>{value}</div>
      {sub && (
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)', marginBottom: 0 }}>
          {sub}
        </div>
      )}
      {(explain || context) && (
        <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--border)' }}>
          {explain && (
            <div style={{
              fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)', lineHeight: 1.6, marginBottom: context ? 6 : 0,
            }}>{explain}</div>
          )}
          {context && (
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }}>
              {context}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Linha de separador com rótulo
function Divider({ label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '20px 0 16px' }}>
      <div style={{ flex: 1, height: '0.5px', background: 'var(--border)' }} />
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.14em' }}>
        {label}
      </span>
      <div style={{ flex: 1, height: '0.5px', background: 'var(--border)' }} />
    </div>
  );
}

export default function ModelosPage() {
  const { isMobile } = useBreakpoint();

  const { data: riscoData,    loading: riscoLoading,    disponivel: riscoDisponivel    } = useApi('/risco');
  const { data: clustersData, loading: clustersLoading, disponivel: clustersDisponivel } = useApi('/clusters');
  const { data: modelosData, loading: modelosLoading, disponivel: modelosDisponivel } = useApi('/previsoes/modelos');

  const m  = riscoDisponivel    ? riscoData?.metricas    : null;
  const km = clustersDisponivel ? clustersData?.metricas : null;
  const ml = modelosDisponivel  ? modelosData?.metricas_lstm    : null;
  const mp = modelosDisponivel  ? modelosData?.metricas_prophet : null;

  const fmtMae = (v) => (v != null ? v.toFixed(2) : '—');
  const fmtPct = (v) => (v != null ? `−${v.toFixed(1)}%` : '—');

  const grid2 = { display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',         gap: 14 };
  const grid3 = { display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)',   gap: 14 };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <PageHeader
        title="Avaliação dos Modelos"
        sub="MÉTRICAS DE PERFORMANCE · CLASSIFICAÇÃO · REGRESSÃO TEMPORAL · CLUSTERING"
      />

      <main style={{ flex: 1, padding: isMobile ? '12px 12px 40px' : '20px 28px 60px', display: 'flex', flexDirection: 'column', gap: 24 }}>

        {/* ── Banner: Por que não acurácia? ─────────────────────────────────── */}
        <div style={{
          background: 'rgba(255,204,0,0.06)',
          border: '1px solid rgba(255,204,0,0.35)',
          borderLeft: '3px solid var(--yellow)',
          borderRadius: 6, padding: '14px 18px',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
            color: 'var(--yellow)', letterSpacing: '0.14em', marginBottom: 8,
          }}>⚠ POR QUE NÃO USAMOS ACURÁCIA?</div>
          <div style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: 'var(--text-sec)', lineHeight: 1.7 }}>
            Com <strong style={{ color: 'var(--text-pri)' }}>248 violações</strong> em{' '}
            <strong style={{ color: 'var(--text-pri)' }}>25.588 incidentes</strong> (desbalanceamento{' '}
            <strong style={{ color: 'var(--yellow)' }}>1:102</strong>), um modelo que simplesmente prevê{' '}
            <em>"sem violação"</em> para todos os casos acertaria{' '}
            <strong style={{ color: 'var(--red)' }}>99% das previsões</strong> — mas ignoraria 100% das violações reais.
            A acurácia não distingue esse cenário de um modelo útil.
            As métricas corretas para este problema são{' '}
            <strong style={{ color: 'var(--teal)' }}>PR-AUC</strong>,{' '}
            <strong style={{ color: 'var(--teal)' }}>Recall</strong> e{' '}
            <strong style={{ color: 'var(--teal)' }}>F1-Score</strong>.
          </div>
        </div>

        {/* ── MODULE 01: XGBoost ────────────────────────────────────────────── */}
        <Module
          n={1}
          title="XGBoost — Classificação de Risco OLA"
          sub={riscoDisponivel ? `${riscoData?.abordagem} · gerado em ${riscoData?.gerado_em}` : 'Modelo de classificação de violação de OLA'}
        >
          {riscoLoading ? (
            <div style={grid3}>{[0,1,2,3,4,5].map(i => <Skeleton key={i} height={160} />)}</div>
          ) : !riscoDisponivel ? (
            <SemDados mensagem="Modelo XGBoost não disponível — execute: python src/pipeline.py --step xgb" />
          ) : (
            <>
              {/* Métricas primárias */}
              <Divider label="MÉTRICAS PRINCIPAIS" />
              <div style={grid3}>
                <MetricCard
                  label="PR-AUC"
                  value={(m?.pr_auc ?? 0).toFixed(3)}
                  sub="Área sob Precisão-Recall"
                  color="var(--teal)"
                  badge={{ text: 'PRIMÁRIA', color: 'var(--teal)' }}
                  explain="Mede a qualidade do modelo em detectar violações em todos os thresholds possíveis. Para dados desbalanceados, é mais informativa que ROC-AUC. Baseline aleatório para desbalanceamento 1:102 é ~1%."
                  context={`≈ ${((m?.pr_auc ?? 0) / 0.0098).toFixed(1)}× acima do baseline aleatório (1%)`}
                />
                <MetricCard
                  label="ROC-AUC"
                  value={(m?.roc_auc ?? 0).toFixed(4)}
                  sub="Área sob a curva ROC"
                  color="var(--teal)"
                  explain="Probabilidade de o modelo ranquear um caso com violação acima de um caso sem violação. 0.5 = aleatório, 1.0 = perfeito. Boa referência de separabilidade geral."
                  context="Acima de 0.7 é considerado discriminação aceitável"
                />
                <MetricCard
                  label="ROC-AUC CV"
                  value={`${(m?.roc_auc_cv_mean ?? 0).toFixed(4)} ± ${(m?.roc_auc_cv_std ?? 0).toFixed(4)}`}
                  sub="Validação cruzada 5-fold estratificada"
                  color="var(--green)"
                  badge={{ text: 'GENERALIZAÇÃO', color: 'var(--green)' }}
                  explain="ROC-AUC medido em 5 subconjuntos de dados não vistos durante o treino. Confirma que o modelo generaliza — não apenas memoriza o conjunto de treino."
                  context={`Desvio padrão ${(m?.roc_auc_cv_std ?? 0).toFixed(4)} indica ${(m?.roc_auc_cv_std ?? 0) < 0.04 ? 'alta estabilidade' : 'variabilidade moderada'}`}
                />
              </div>

              {/* Métricas de threshold */}
              <Divider label="MÉTRICAS NO THRESHOLD ÓTIMO (F1-MÁXIMO)" />
              <div style={grid3}>
                <MetricCard
                  label="RECALL"
                  value={`${((m?.recall_violacao ?? 0) * 100).toFixed(1)}%`}
                  sub="Sensibilidade — violações detectadas"
                  color="var(--orange)"
                  explain="Das violações reais no período de teste, qual % o modelo identificou. Falsos negativos (violações perdidas) têm custo operacional alto — o incidente estoura o OLA sem intervenção preventiva."
                  context={`${m?.violacoes_capturadas ?? 0} de ${m?.violacoes_reais ?? 0} violações detectadas no teste`}
                />
                <MetricCard
                  label="PRECISION"
                  value={`${((m?.precision_violacao ?? 0) * 100).toFixed(1)}%`}
                  sub="Precisão — alertas corretos"
                  color="var(--orange)"
                  explain="Dos alertas emitidos pelo modelo, qual % era uma violação real. Alarmes falsos têm custo operacional mas são menos críticos que violações perdidas."
                  context={`${m?.fp ?? 0} alarmes falsos para ${m?.tp ?? 0} detecções corretas`}
                />
                <MetricCard
                  label="F1-SCORE"
                  value={`${((m?.f1_violacao ?? 0) * 100).toFixed(1)}%`}
                  sub="Média harmônica Precision × Recall"
                  color="var(--orange)"
                  explain="Equilibra Precision e Recall em um único valor. O threshold foi otimizado para maximizar este score — representa o melhor equilíbrio dado o desbalanceamento 1:102."
                  context={`Threshold ótimo: ${(riscoData?.threshold_otimizado ?? 0).toFixed(4)} · scale_pos_weight: ${riscoData?.scale_pos_weight ?? '—'}`}
                />
              </div>

              {/* Matriz de confusão */}
              <Divider label="MATRIZ DE CONFUSÃO — CONJUNTO DE TESTE" />
              <div style={{ display: 'flex', flexDirection: isMobile ? 'column' : 'row', gap: 20, alignItems: 'flex-start' }}>
                <div style={{ flex: '0 0 auto' }}>
                  {/* Header */}
                  <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr 1fr', marginBottom: 4 }}>
                    <div />
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', textAlign: 'center', letterSpacing: '0.1em' }}>PREVIU NORMAL</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', textAlign: 'center', letterSpacing: '0.1em' }}>PREVIU VIOLAÇÃO</div>
                  </div>
                  {[
                    {
                      rowLabel: 'REAL: NORMAL',
                      rowSub: `(${((m?.tn ?? 0) + (m?.fp ?? 0)).toLocaleString('pt-BR')} incidentes)`,
                      left:  { label: 'TN', value: (m?.tn ?? 0).toLocaleString('pt-BR'), sub: 'Acerto: normal identificado', color: 'var(--green)', bg: 'rgba(52,199,89,0.07)' },
                      right: { label: 'FP', value: m?.fp ?? 0, sub: 'Alarme falso', color: 'var(--orange)', bg: 'rgba(255,159,10,0.08)' },
                    },
                    {
                      rowLabel: 'REAL: VIOLAÇÃO',
                      rowSub: `(${(m?.violacoes_reais ?? 0)} incidentes)`,
                      left:  { label: 'FN', value: m?.fn ?? 0, sub: 'Violação perdida ⚠', color: 'var(--red)',   bg: 'rgba(255,45,85,0.10)' },
                      right: { label: 'TP', value: m?.tp ?? 0, sub: 'Acerto: violação detectada', color: 'var(--green)', bg: 'rgba(52,199,89,0.07)' },
                    },
                  ].map(({ rowLabel, rowSub, left, right }) => (
                    <div key={rowLabel} style={{ display: 'grid', gridTemplateColumns: '140px 1fr 1fr', gap: 6, marginBottom: 6 }}>
                      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-sec)', fontWeight: 600 }}>{rowLabel}</div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)' }}>{rowSub}</div>
                      </div>
                      {[left, right].map(cell => (
                        <div key={cell.label} style={{
                          background: cell.bg, border: `1px solid ${cell.color}33`,
                          borderRadius: 6, padding: '10px 12px', textAlign: 'center',
                        }}>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: cell.color, fontWeight: 700, letterSpacing: '0.1em', marginBottom: 4 }}>
                            {cell.label}
                          </div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700, color: cell.color, lineHeight: 1 }}>
                            {cell.value}
                          </div>
                          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: 'var(--text-muted)', marginTop: 4 }}>
                            {cell.sub}
                          </div>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>

                {/* Legenda da matriz */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10, paddingTop: 28 }}>
                  {[
                    { label: 'TP — Verdadeiro Positivo', color: 'var(--green)', text: 'Modelo previu violação e a violação ocorreu. Resultado desejado.' },
                    { label: 'TN — Verdadeiro Negativo', color: 'var(--green)', text: 'Modelo previu normalidade e não houve violação. Resultado correto.' },
                    { label: 'FP — Falso Positivo',      color: 'var(--orange)', text: 'Alarme falso. Equipe investigou mas não havia violação. Custo operacional baixo.' },
                    { label: 'FN — Falso Negativo',      color: 'var(--red)',    text: 'Violação perdida. Incidente estourou OLA sem alerta preventivo. Custo mais alto.' },
                  ].map(({ label, color, text }) => (
                    <div key={label} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                      <div style={{ width: 3, flexShrink: 0, alignSelf: 'stretch', background: color, borderRadius: 2 }} />
                      <div>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color, fontWeight: 700, marginBottom: 2 }}>{label}</div>
                        <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)', lineHeight: 1.5 }}>{text}</div>
                      </div>
                    </div>
                  ))}
                  <div style={{
                    marginTop: 6, padding: '10px 12px',
                    background: 'var(--surface3)', border: '1px solid var(--border)', borderRadius: 6,
                    fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-sec)',
                  }}>
                    <strong style={{ color: 'var(--text-pri)' }}>Total de teste:</strong>{' '}
                    {(m?.total_teste ?? 0).toLocaleString('pt-BR')} incidentes ·{' '}
                    <strong style={{ color: 'var(--red)' }}>{m?.violacoes_reais ?? 0} violações reais</strong>{' '}
                    ({(((m?.violacoes_reais ?? 0) / (m?.total_teste ?? 1)) * 100).toFixed(2)}% da base de teste)
                  </div>
                </div>
              </div>

              {/* PR-AUC CV */}
              <Divider label="CROSS-VALIDATION — PR-AUC" />
              <div style={grid2}>
                <MetricCard
                  label="PR-AUC CV (MEAN)"
                  value={(m?.pr_auc_cv_mean ?? 0).toFixed(4)}
                  sub="Média em 5 folds estratificados"
                  color="var(--teal)"
                  explain="PR-AUC medido na validação cruzada — mais representativo que o valor único no conjunto de teste. Estratificado para garantir proporção de violações em cada fold."
                  context={`Desvio padrão: ±${(m?.pr_auc_cv_std ?? 0).toFixed(4)}`}
                />
                <MetricCard
                  label="INTERPRETAÇÃO DO MODELO"
                  value="Uso contínuo"
                  sub="Probabilidades > threshold binário"
                  color="var(--text-sec)"
                  explain="O modelo é mais útil como score contínuo do que como classificador binário. Probabilidades acima de 15% indicam atenção; acima de 30% indicam alto risco — independente do threshold ótimo."
                  context={`Threshold F1-ótimo: ${(riscoData?.threshold_otimizado ?? 0).toFixed(4)} · threshold p/ recall ≥70%: ${riscoData?.threshold_recall_70 ?? '—'}`}
                />
              </div>
            </>
          )}
        </Module>

        {/* ── MODULE 02: Previsão de Volume ─────────────────────────────────── */}
        <Module
          n={2}
          title="Previsão de Volume — Prophet & LSTM"
          sub={modelosDisponivel
            ? `modelo ativo: ${modelosData?.modelo_ativo ?? '—'} · MAE holdout: ${fmtMae(modelosData?.mae_modelo_ativo)}`
            : 'Erro médio absoluto (MAE) em incidentes/dia · hierarquia LSTM v2 > Prophet MC > Prophet Original'}
        >
          {/* Callout: o que é MAE */}
          <div style={{
            background: 'rgba(90,200,250,0.06)', border: '1px solid rgba(90,200,250,0.25)',
            borderLeft: '3px solid var(--teal)', borderRadius: 6, padding: '12px 16px', marginBottom: 20,
          }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: 'var(--teal)', letterSpacing: '0.12em', marginBottom: 6 }}>
              O QUE É MAE (MEAN ABSOLUTE ERROR)?
            </div>
            <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)', lineHeight: 1.65 }}>
              Erro Médio Absoluto — a média de{' '}
              <em>|previsão − real|</em> em incidentes por dia. MAE de 13 significa que a previsão erra em média 13 incidentes/dia.
              É a métrica principal para séries temporais de volume: intuitiva, interpretável e não penaliza erros grandes desproporcionalmente (ao contrário do RMSE).
            </div>
          </div>

          {modelosLoading ? (
            <div style={grid3}>{[0,1,2,3,4,5].map(i => <Skeleton key={i} height={180} />)}</div>
          ) : !modelosDisponivel ? (
            <SemDados mensagem="Modelos de previsão não disponíveis — execute: python src/pipeline.py --step lstm" />
          ) : (
            <>
              <Divider label="LSTM V2 — MELHOR MODELO ATIVO" />
              <div style={grid3}>
                <MetricCard
                  label="MAE HOLDOUT — TOTAL"
                  value={fmtMae(ml?.mae_total)}
                  sub="Média em 92 dias de holdout real (out–dez 2025)"
                  color="var(--green)"
                  badge={{ text: 'MODELO ATIVO', color: 'var(--teal)' }}
                  explain="Erro médio absoluto medido em 92 dias completamente fora do treino (holdout). Dados 100% reais, sem Monte Carlo. A separação estrita evita vazamento de dados futuros."
                  context={ml?.arquitetura ?? '—'}
                />
                <MetricCard
                  label="MAE HOLDOUT — P2"
                  value={fmtMae(ml?.mae_p2)}
                  sub="Alta prioridade · OLA ≤ 4h"
                  color="var(--green)"
                  explain="Incidentes P2 têm menor volume diário — mais fáceis de prever com precisão. MAE baixo representa alta qualidade de previsão para a classe mais crítica."
                  context="P2 é a prioridade que excedeu a meta em 2025 (42 vs meta 37)"
                />
                <MetricCard
                  label="MAE HOLDOUT — P3"
                  value={fmtMae(ml?.mae_p3)}
                  sub="Média prioridade · OLA ≤ 12h"
                  color="var(--teal)"
                  explain="P3 tem maior volume diário e mais variabilidade. O erro é aceitável dado que o volume médio diário de P3 é ~50 incidentes."
                  context="P3 ficou dentro da meta em 2025 (196 vs meta 247)"
                />
              </div>

              <Divider label="PROPHET ENSEMBLE — FALLBACK" />
              <div style={grid3}>
                <MetricCard
                  label="MAE D+1 — TOTAL"
                  value={fmtMae(mp?.mae_d1_total)}
                  sub="Erro previsão 1 dia à frente"
                  color="var(--orange)"
                  explain="MAE do Prophet Ensemble (v5+v6) para previsão do próximo dia. Calculado por cross-validation (initial=180d). Usado como fallback quando LSTM não está disponível."
                  context="Prophet 2025-only · ensemble v5 (4 lags) + v6 (+ is_dia_util)"
                />
                <MetricCard
                  label="MAE D+7 — TOTAL"
                  value={fmtMae(mp?.mae_d7_total)}
                  sub="Erro previsão 7 dias à frente"
                  color="var(--orange)"
                  explain="Para horizontes maiores, o Prophet seleciona automaticamente o modelo (v5 ou v6) com menor MAE histórico para aquele horizonte específico — reduzindo o erro médio."
                  context="Seleção por horizonte via cross-validation"
                />
                <MetricCard
                  label="LSTM vs PROPHET"
                  value={fmtPct(ml?.melhora_pct_vs_prophet)}
                  sub="Redução de erro no holdout de 92 dias"
                  color="var(--green)"
                  badge={{ text: 'MELHORA', color: 'var(--green)' }}
                  explain={`No holdout de 92 dias (out–dez 2025), o LSTM v2 reduziu o MAE vs Prophet rolling. O LSTM captura melhor padrões de longo prazo após 3 anos de dados.`}
                  context={`Prophet holdout MAE = ${fmtMae(ml?.mae_prophet_holdout_92d)} · LSTM holdout MAE = ${fmtMae(ml?.mae_total)}`}
                />
              </div>

              {/* Tabela comparativa */}
              <Divider label="COMPARAÇÃO DIRETA — HOLDOUT 92 DIAS" />
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid var(--border)' }}>
                      {['Modelo', 'Período', 'MAE Total', 'MAE P2', 'MAE P3', 'Status'].map(h => (
                        <th key={h} style={{ padding: '6px 12px', textAlign: 'left', color: 'var(--text-muted)', fontSize: 9, letterSpacing: '0.12em', fontWeight: 600 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { model: 'LSTM v2', period: 'Holdout real 92d', total: fmtMae(ml?.mae_total), p2: fmtMae(ml?.mae_p2), p3: fmtMae(ml?.mae_p3), status: 'ATIVO', statusColor: 'var(--teal)' },
                      { model: 'Prophet MC', period: 'Holdout real 92d', total: fmtMae(ml?.mae_prophet_holdout_92d), p2: '—', p3: '—', status: 'FALLBACK', statusColor: 'var(--text-muted)' },
                      { model: 'Prophet Orig.', period: 'Cross-validation', total: fmtMae(mp?.mae_d1_total), p2: fmtMae(mp?.mae_d1_p2), p3: fmtMae(mp?.mae_d1_p3), status: 'FALLBACK', statusColor: 'var(--text-muted)' },
                    ].map((row, i) => (
                      <tr key={i} style={{ borderBottom: '0.5px solid var(--border)', background: i === 0 ? 'rgba(90,200,250,0.04)' : 'transparent' }}>
                        <td style={{ padding: '8px 12px', color: i === 0 ? 'var(--teal)' : 'var(--text-sec)', fontWeight: i === 0 ? 700 : 400 }}>{row.model}</td>
                        <td style={{ padding: '8px 12px', color: 'var(--text-muted)', fontSize: 10 }}>{row.period}</td>
                        <td style={{ padding: '8px 12px', color: i === 0 ? 'var(--green)' : 'var(--text-sec)', fontWeight: i === 0 ? 700 : 400 }}>{row.total}</td>
                        <td style={{ padding: '8px 12px', color: 'var(--text-sec)' }}>{row.p2}</td>
                        <td style={{ padding: '8px 12px', color: 'var(--text-sec)' }}>{row.p3}</td>
                        <td style={{ padding: '8px 12px' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 8, color: row.statusColor, background: `${row.statusColor}15`, border: `1px solid ${row.statusColor}33`, borderRadius: 3, padding: '2px 6px' }}>
                            {row.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Module>

        {/* ── MODULE 03: K-Means ────────────────────────────────────────────── */}
        <Module
          n={3}
          title="K-Means — Qualidade da Segmentação"
          sub={clustersDisponivel ? `K=${clustersData?.k} clusters · ${km?.features_usadas} features · ${(km?.total_incidentes ?? 0).toLocaleString('pt-BR')} incidentes · gerado em ${clustersData?.gerado_em}` : 'Modelo de segmentação de padrões de incidentes'}
        >
          {clustersLoading ? (
            <div style={grid3}>{[0,1,2].map(i => <Skeleton key={i} height={180} />)}</div>
          ) : !clustersDisponivel ? (
            <SemDados mensagem="Modelo K-Means não disponível — execute: python src/pipeline.py --step km" />
          ) : (
            <>
              {/* Callout sobre métricas de clustering */}
              <div style={{
                background: 'rgba(90,200,250,0.06)', border: '1px solid rgba(90,200,250,0.25)',
                borderLeft: '3px solid var(--teal)', borderRadius: 6, padding: '12px 16px', marginBottom: 20,
              }}>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, color: 'var(--teal)', letterSpacing: '0.12em', marginBottom: 6 }}>
                  COMO AVALIAR CLUSTERING?
                </div>
                <div style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)', lineHeight: 1.65 }}>
                  Ao contrário de classificação, não há uma "resposta certa" para comparar. O K ideal foi selecionado por{' '}
                  <strong style={{ color: 'var(--text-pri)' }}>voto majoritário</strong> entre três métricas complementares — Silhouette, CH e DB —
                  candidato a K ímpar ≥ 5. Cada métrica captura um aspecto diferente da qualidade dos clusters.
                </div>
              </div>

              <div style={grid3}>
                <MetricCard
                  label="SILHOUETTE SCORE"
                  value={(km?.silhouette_score ?? 0).toFixed(4)}
                  sub="Coesão interna vs separação entre clusters"
                  color={(km?.silhouette_score ?? 0) > 0.4 ? 'var(--green)' : (km?.silhouette_score ?? 0) > 0.2 ? 'var(--orange)' : 'var(--red)'}
                  explain="Mede quão similar cada ponto é ao seu próprio cluster em comparação aos outros clusters. Varia de −1 a +1. Valores > 0.5 são excelentes; 0.2–0.5 são razoáveis; < 0.2 indicam sobreposição natural dos dados."
                  context="Dados de comportamento operacional raramente excedem 0.3 — sobreposição é esperada"
                />
                <MetricCard
                  label="CALINSKI-HARABÁSZ"
                  value={(km?.calinski_harabasz ?? 0).toFixed(0)}
                  sub="Razão dispersão entre/dentro dos clusters"
                  color="var(--teal)"
                  explain="Razão entre a dispersão inter-cluster e a dispersão intra-cluster. Quanto maior o valor, mais bem separados e compactos são os clusters. Não tem escala fixa — usado comparativamente entre diferentes K."
                  context="Maior é melhor · usado como 1 dos 3 votos na seleção do K"
                />
                <MetricCard
                  label="DAVIES-BOULDIN"
                  value={(km?.davies_bouldin ?? 0).toFixed(4)}
                  sub="Similaridade média entre clusters vizinhos"
                  color={(km?.davies_bouldin ?? 0) < 1.5 ? 'var(--green)' : (km?.davies_bouldin ?? 0) < 2.0 ? 'var(--orange)' : 'var(--red)'}
                  explain="Média da razão entre a compacidade intra-cluster e a distância entre centroides. Menor é melhor. < 1.5 = bom; 1.5–2.0 = aceitável; > 2.0 = clusters sobrepostos."
                  context="Menor é melhor · usado como 1 dos 3 votos na seleção do K"
                />
              </div>

              <Divider label="CONFIGURAÇÃO DO MODELO" />
              <div style={grid3}>
                <MetricCard
                  label="K SELECIONADO"
                  value={clustersData?.k ?? '—'}
                  sub="Clusters identificados"
                  color="var(--teal)"
                  explain="O K foi selecionado avaliando K de 2 a 10. Apenas K ímpares ≥ 5 foram elegíveis (para garantir granularidade mínima). O vencedor foi o K com maioria de votos entre as 3 métricas."
                  context={`Metodologia: ${clustersData?.metodologia ?? '—'}`}
                />
                <MetricCard
                  label="VARIÂNCIA PCA 2D"
                  value={`${((km?.pca_variancia_2d ?? 0) * 100).toFixed(1)}%`}
                  sub="Explicado pelas 2 componentes principais"
                  color="var(--text-sec)"
                  explain="Para visualização, os dados são reduzidos de 11 dimensões para 2 via PCA. A variância explicada indica quanto da estrutura original é preservada na visualização 2D dos clusters."
                  context="Quanto maior, mais fiel é a visualização 2D à estrutura real"
                />
                <MetricCard
                  label="INÉRCIA FINAL"
                  value={(km?.inertia ?? 0).toFixed(0)}
                  sub="Soma dos quadrados intra-cluster"
                  color="var(--text-sec)"
                  explain="Soma das distâncias quadráticas de cada ponto ao centroide do seu cluster. Usada para o gráfico de cotovelo — não tem interpretação absoluta, mas decresce com K maior."
                  context={`${(km?.total_incidentes ?? 0).toLocaleString('pt-BR')} incidentes · ${km?.features_usadas} features`}
                />
              </div>
            </>
          )}
        </Module>

      </main>
    </div>
  );
}
