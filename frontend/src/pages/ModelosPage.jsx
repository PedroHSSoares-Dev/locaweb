import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Cell, LabelList } from 'recharts';
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

const SHAP_LABELS = {
  grupo_viol_rate:  'Taxa histórica de violação do grupo de atendimento',
  rolling_30d:      'Volume médio de incidentes nos últimos 30 dias',
  rolling_7d:       'Volume médio de incidentes nos últimos 7 dias',
  aberto_por_enc:   'Agente responsável pela abertura',
  produto_freq:     'Frequência do produto afetado',
  produto_enc:      'Produto afetado',
  categoria_enc:    'Categoria do incidente',
  lag_7d:           'Volume de incidentes 7 dias atrás',
  hora:             'Hora de abertura do incidente',
  semana_ano:       'Semana do ano',
  subcategoria_enc: 'Subcategoria',
  grupo_freq:       'Frequência do grupo designado',
  dia_mes:          'Dia do mês',
  grupo_enc:        'Grupo de atendimento designado',
  mes_cos:          'Sazonalidade mensal',
};

function ExplainBox({ title, color = 'var(--purple, #a78bfa)', items }) {
  return (
    <div style={{
      marginTop: 24,
      background: `color-mix(in srgb, ${color} 6%, transparent)`,
      border: `1px solid color-mix(in srgb, ${color} 30%, transparent)`,
      borderLeft: `3px solid ${color}`,
      borderRadius: 6, padding: '14px 18px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700,
        color, letterSpacing: '0.14em', marginBottom: 12,
      }}>
        {title}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items.map((item, i) => (
          <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 700,
              color, background: `color-mix(in srgb, ${color} 15%, transparent)`,
              border: `1px solid color-mix(in srgb, ${color} 30%, transparent)`,
              borderRadius: 3, padding: '2px 6px', whiteSpace: 'nowrap', marginTop: 1,
            }}>{item.tag}</span>
            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)', lineHeight: 1.6 }}>
              {item.text}
            </span>
          </div>
        ))}
      </div>
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

              {/* SHAP Feature Importance Chart */}
              {riscoData?.feature_importance_shap?.length > 0 && (<>
                <Divider label="FEATURE IMPORTANCE — SHAP (TOP 10)" />
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart
                    layout="vertical"
                    data={riscoData.feature_importance_shap.slice(0, 10).map(f => ({
                      name: SHAP_LABELS[f.feature] ?? f.feature,
                      value: f.shap_mean_abs,
                    })).reverse()}
                    margin={{ top: 0, right: 40, left: 8, bottom: 0 }}
                  >
                    <XAxis type="number" tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }} tickFormatter={v => v.toFixed(2)} />
                    <YAxis type="category" dataKey="name" width={210} tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-sec)' }} />
                    <Tooltip
                      contentStyle={{ background: 'var(--surface3)', border: '1px solid var(--border)', borderRadius: 6, fontFamily: 'var(--font-mono)', fontSize: 10 }}
                      formatter={v => [v.toFixed(4), 'SHAP médio |valor|']}
                    />
                    <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                      {riscoData.feature_importance_shap.slice(0, 10).map((_, i) => (
                        <Cell key={i} fill={i === 9 ? 'var(--teal)' : `rgba(90,200,250,${0.35 + (i / 9) * 0.65})`} />
                      ))}
                      <LabelList dataKey="value" position="right" formatter={v => v.toFixed(3)} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </>)}

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

              {/* Explicabilidade XGBoost */}
              {riscoData?.feature_importance_shap?.length > 0 && (() => {
                const top3 = riscoData.feature_importance_shap.slice(0, 3);
                const rec  = m?.recall_violacao ?? 0;
                const fn   = m?.fn ?? 0;
                const tp   = m?.violacoes_capturadas ?? 0;
                const total = tp + fn;
                return (
                  <ExplainBox
                    title="INTERPRETAÇÃO OPERACIONAL — O QUE O MODELO APRENDEU"
                    color="var(--purple, #a78bfa)"
                    items={[
                      {
                        tag: 'PREDITOR #1',
                        text: <>
                          <strong style={{ color: 'var(--text-pri)' }}>{SHAP_LABELS[top3[0].feature] ?? top3[0].feature}</strong>
                          {' '}é o fator mais determinante do risco (SHAP médio {top3[0].shap_mean_abs.toFixed(3)}). Grupos com histórico de violações frequentes concentram a maior parte dos alertas — o modelo reconhece padrões recorrentes por equipe.
                        </>,
                      },
                      {
                        tag: 'PREDITOR #2',
                        text: <>
                          <strong style={{ color: 'var(--text-pri)' }}>{SHAP_LABELS[top3[1].feature] ?? top3[1].feature}</strong>
                          {' '}(SHAP {top3[1].shap_mean_abs.toFixed(3)}) e <strong style={{ color: 'var(--text-pri)' }}>{SHAP_LABELS[top3[2].feature] ?? top3[2].feature}</strong>
                          {' '}(SHAP {top3[2].shap_mean_abs.toFixed(3)}) indicam que períodos de alta demanda elevam o risco de violação — sobrecarga operacional é um fator independente do grupo.
                        </>,
                      },
                      {
                        tag: 'THRESHOLD',
                        text: <>
                          Com threshold recall≥70%, o modelo captura <strong style={{ color: 'var(--text-pri)' }}>{tp} de {total} violações reais</strong> no conjunto de teste ({(rec * 100).toFixed(0)}% de recall). O uso como <em>score contínuo</em> permite priorizar a fila de incidentes abertos sem depender de um corte binário.
                        </>,
                      },
                      {
                        tag: 'LIMITAÇÃO',
                        text: 'Desbalanceamento 1:102 limita a precision (3%). Recomendado para triagem — um analista valida os incidentes sinalizados, não para alertas automáticos sem revisão humana.',
                      },
                    ]}
                  />
                );
              })()}
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

              {/* MAE Comparison Chart */}
              {modelosDisponivel && ml && (<>
                <Divider label="COMPARATIVO MAE — GRÁFICO" />
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    data={[
                      { modelo: 'LSTM v2',       total: ml.mae_total,                    p2: ml.mae_p2,    p3: ml.mae_p3 },
                      { modelo: 'Prophet MC',     total: ml.mae_prophet_holdout_92d ?? null, p2: null,     p3: null },
                      { modelo: 'Prophet Orig.',  total: mp?.mae_d1_total ?? null,        p2: mp?.mae_d1_p2 ?? null, p3: mp?.mae_d1_p3 ?? null },
                    ]}
                    margin={{ top: 8, right: 20, left: 0, bottom: 0 }}
                  >
                    <XAxis dataKey="modelo" tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-sec)' }} />
                    <YAxis tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }} unit=" inc" />
                    <Tooltip
                      contentStyle={{ background: 'var(--surface3)', border: '1px solid var(--border)', borderRadius: 6, fontFamily: 'var(--font-mono)', fontSize: 10 }}
                      formatter={(v, name) => [v != null ? `${v.toFixed(2)} inc/dia` : '—', name.toUpperCase()]}
                    />
                    <Legend wrapperStyle={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)' }} />
                    <Bar dataKey="total" name="Total" fill="var(--teal)"   radius={[3,3,0,0]}>
                      <LabelList dataKey="total" position="top" formatter={v => v != null ? v.toFixed(1) : ''} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }} />
                    </Bar>
                    <Bar dataKey="p2"    name="P2"    fill="var(--orange)" radius={[3,3,0,0]}>
                      <LabelList dataKey="p2"    position="top" formatter={v => v != null ? v.toFixed(1) : ''} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }} />
                    </Bar>
                    <Bar dataKey="p3"    name="P3"    fill="rgba(90,200,250,0.45)" radius={[3,3,0,0]}>
                      <LabelList dataKey="p3"    position="top" formatter={v => v != null ? v.toFixed(1) : ''} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </>)}

              {/* Explicabilidade Prophet/LSTM */}
              {modelosDisponivel && (() => {
                const maeTotal   = ml?.mae_total;
                const maeP2      = ml?.mae_p2;
                const melhora    = ml?.melhora_pct_vs_prophet;
                const volMedio   = 70; // ~70 incidentes/dia KPI (P2+P3)
                const pctErro    = maeTotal != null ? ((maeTotal / volMedio) * 100).toFixed(1) : null;
                return (
                  <ExplainBox
                    title="INTERPRETAÇÃO OPERACIONAL — O QUE O MODELO PREVÊ"
                    color="var(--teal)"
                    items={[
                      {
                        tag: 'PRECISÃO',
                        text: <>
                          O LSTM v2 erra em média <strong style={{ color: 'var(--text-pri)' }}>{fmtMae(maeTotal)} incidentes/dia</strong> no conjunto de holdout real (out–dez 2025).
                          {pctErro && <> Isso representa <strong style={{ color: 'var(--text-pri)' }}>{pctErro}%</strong> do volume médio diário — margem operacionalmente aceitável para planejamento de capacidade.</>}
                        </>,
                      },
                      {
                        tag: 'P2 CRÍTICO',
                        text: <>
                          Para incidentes P2 (OLA ≤ 4h), o erro médio é de apenas <strong style={{ color: 'var(--text-pri)' }}>{fmtMae(maeP2)} incidentes/dia</strong> — a classe mais crítica é também a mais previsível por ter menor variabilidade de volume.
                        </>,
                      },
                      {
                        tag: 'EVOLUÇÃO',
                        text: <>
                          O LSTM reduziu o erro em <strong style={{ color: 'var(--text-pri)' }}>{fmtPct(melhora)}</strong> comparado ao Prophet no mesmo período de holdout. O ganho vem da capacidade do LSTM de capturar dependências de longo prazo nos 3 anos de histórico.
                        </>,
                      },
                      {
                        tag: 'USO',
                        text: 'As previsões permitem antecipar picos de demanda e dimensionar equipes com até 7 dias de antecedência. Não substituem monitoramento em tempo real — são complementares ao XGBoost (risco por incidente).',
                      },
                    ]}
                  />
                );
              })()}
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

              {/* Cluster Violation Rate Chart */}
              {clustersDisponivel && clustersData?.clusters?.length > 0 && (<>
                <Divider label="TAXA DE VIOLAÇÃO OLA POR CLUSTER" />
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart
                    data={[...clustersData.clusters]
                      .sort((a, b) => b.taxaViolacao - a.taxaViolacao)
                      .map(c => ({ name: `C${c.id}`, label: c.label, viol: c.taxaViolacao, tam: c.tamanho }))}
                    margin={{ top: 8, right: 20, left: 0, bottom: 8 }}
                  >
                    <XAxis dataKey="name" tick={{ fontFamily: 'var(--font-mono)', fontSize: 10, fill: 'var(--text-sec)' }} />
                    <YAxis tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }} unit="%" tickFormatter={v => v.toFixed(1)} />
                    <Tooltip
                      contentStyle={{ background: 'var(--surface3)', border: '1px solid var(--border)', borderRadius: 6, fontFamily: 'var(--font-mono)', fontSize: 10 }}
                      formatter={(v, name) => name === 'viol' ? [`${v.toFixed(3)}%`, 'Taxa violação OLA'] : [v.toLocaleString('pt-BR'), 'Incidentes']}
                      labelFormatter={(_, payload) => payload?.[0]?.payload?.label ?? ''}
                    />
                    <Bar dataKey="viol" name="viol" radius={[3,3,0,0]}>
                      {[...clustersData.clusters]
                        .sort((a, b) => b.taxaViolacao - a.taxaViolacao)
                        .map((c, i, arr) => {
                          const max = arr[0].taxaViolacao;
                          const ratio = c.taxaViolacao / max;
                          return <Cell key={i} fill={`rgba(${Math.round(255*ratio)},${Math.round(140*(1-ratio*0.5))},89,0.85)`} />;
                        })}
                      <LabelList dataKey="viol" position="top" formatter={v => `${v.toFixed(2)}%`} style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-muted)' }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </>)}

              {/* Tabela comparação de K */}
              {clustersData?.comparacao_k?.length > 0 && (() => {
                const rows = clustersData.comparacao_k;
                const kMin = clustersData.k_min_utilizado ?? 5;
                // elegível = K ímpar >= kMin (mesma regra do modelo)
                const elegiveis = rows.filter(r => r.k >= kMin && r.k % 2 === 1);
                const bestSil = Math.max(...elegiveis.map(r => r.silhouette));
                const bestCH  = Math.max(...elegiveis.map(r => r.calinski_harabasz));
                const bestDB  = Math.min(...elegiveis.map(r => r.davies_bouldin));
                const bestIn  = Math.min(...elegiveis.map(r => r.inertia));
                const elegivel = r => r.k >= kMin && r.k % 2 === 1;
                const cellStyle = (isBest, isElegivel) => ({
                  padding: '6px 12px',
                  textAlign: 'right',
                  color: isBest ? 'var(--green)' : isElegivel ? 'var(--text-sec)' : 'var(--text-muted)',
                  fontWeight: isBest ? 700 : 400,
                  opacity: isElegivel ? 1 : 0.5,
                });
                return (
                  <div style={{ marginTop: 24 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 2, color: 'var(--text-muted)', marginBottom: 10 }}>
                      COMPARAÇÃO DE K — JUSTIFICATIVA DA ESCOLHA
                    </div>
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, fontFamily: 'var(--font-mono)' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--border)' }}>
                            {['K', 'Silhouette ↑', 'Calinski-H ↑', 'Davies-B ↓', 'Inércia ↓'].map(h => (
                              <th key={h} style={{ padding: '6px 12px', textAlign: 'right', color: 'var(--text-muted)', fontWeight: 600, whiteSpace: 'nowrap' }}>{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {rows.map(row => {
                            const el = elegivel(row);
                            const trStyle = row.selecionado
                              ? { background: 'var(--surface-alt)', outline: '1.5px solid var(--accent)', outlineOffset: '-1px' }
                              : { borderBottom: '1px solid var(--border)', background: 'transparent' };
                            return (
                              <tr key={row.k} style={trStyle}>
                                <td style={{ padding: '6px 12px', textAlign: 'right', fontWeight: row.selecionado ? 700 : 400, color: row.selecionado ? 'var(--accent)' : el ? 'var(--text-pri)' : 'var(--text-muted)', opacity: el ? 1 : 0.5 }}>
                                  {row.k}{row.selecionado ? ' ✓' : ''}
                                </td>
                                <td style={cellStyle(el && row.silhouette === bestSil, el)}>{row.silhouette.toFixed(4)}</td>
                                <td style={cellStyle(el && row.calinski_harabasz === bestCH, el)}>{row.calinski_harabasz.toFixed(0)}</td>
                                <td style={cellStyle(el && row.davies_bouldin === bestDB, el)}>{row.davies_bouldin.toFixed(4)}</td>
                                <td style={cellStyle(el && row.inertia === bestIn, el)}>{row.inertia.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 8 }}>
                      Verde = melhor entre candidatos elegíveis · linhas esmaecidas = K inelegível (par ou abaixo de {kMin}) · seleção por voto majoritário: Silhouette, Calinski-Harabász e Davies-Bouldin
                    </div>
                  </div>
                );
              })()}

              {/* Explicabilidade K-Means */}
              {clustersDisponivel && clustersData?.clusters?.length > 0 && (() => {
                const sorted   = [...clustersData.clusters].sort((a, b) => b.taxaViolacao - a.taxaViolacao);
                const top      = sorted[0];
                const bottom   = sorted[sorted.length - 1];
                const total    = clustersData.clusters.reduce((s, c) => s + c.tamanho, 0);
                const topPct   = ((top.tamanho / total) * 100).toFixed(1);
                return (
                  <ExplainBox
                    title="INTERPRETAÇÃO OPERACIONAL — O QUE OS CLUSTERS REVELAM"
                    color="var(--orange)"
                    items={[
                      {
                        tag: 'MAIOR RISCO',
                        text: <>
                          <strong style={{ color: 'var(--text-pri)' }}>{top.label}</strong> (Cluster {top.id}) apresenta a maior taxa de violação OLA: <strong style={{ color: 'var(--red)' }}>{top.taxaViolacao.toFixed(2)}%</strong> dos incidentes desse grupo violam o prazo. Representa {topPct}% do volume total — foco prioritário de monitoramento.
                        </>,
                      },
                      {
                        tag: 'MENOR RISCO',
                        text: <>
                          <strong style={{ color: 'var(--text-pri)' }}>{bottom.label}</strong> (Cluster {bottom.id}) tem a menor taxa de violação (<strong style={{ color: 'var(--green)' }}>{bottom.taxaViolacao.toFixed(2)}%</strong>). Serve como referência de operação saudável — seus padrões (hora, produto, grupo) devem ser comparados com os clusters de alto risco para identificar diferenças acionáveis.
                        </>,
                      },
                      {
                        tag: 'SILHOUETTE',
                        text: <>
                          Score de {clustersData.silhouette?.toFixed(4)} indica sobreposição moderada entre grupos — esperado em dados operacionais de TI sem segmentação natural rígida. O valor é consistente entre K=5, 7 e 9, confirmando que os grupos identificados são estáveis e não artefatos do algoritmo.
                        </>,
                      },
                      {
                        tag: 'USO',
                        text: 'Os clusters permitem criar políticas diferenciadas por perfil operacional — SLAs mais apertados para grupos de alto risco, roteiros de escalada distintos por período do dia e prioridade.',
                      },
                    ]}
                  />
                );
              })()}
            </>
          )}
        </Module>

      </main>
    </div>
  );
}
