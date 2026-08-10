import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  ArrowDownToLine,
  ArrowUpFromLine,
  DatabaseZap,
  LoaderCircle,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { getAdminUsage } from '../services/adminUsage';

const PERIODS = [
  { value: 7, label: '7D' },
  { value: 30, label: '30D' },
  { value: 90, label: '90D' },
  { value: 0, label: 'TUDO' },
];

const STATUS_LABELS = { active: 'ATIVO', pending: 'PENDENTE', disabled: 'DESATIVADO' };

const EMPTY_TOTALS = {
  requests: 0,
  generated_responses: 0,
  cache_hits: 0,
  input_tokens: 0,
  output_tokens: 0,
  total_tokens: 0,
  reasoning_tokens: 0,
  cached_tokens: 0,
  saved_tokens: 0,
};

const integer = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });

function formatNumber(value) {
  return integer.format(Number(value) || 0);
}

function formatDate(value) {
  if (!value) return 'A PARTIR DESTE DEPLOY';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'A PARTIR DESTE DEPLOY';
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date).replace('.', '').toUpperCase();
}

function UsageMetric({ icon, value, label, detail, tone = 'teal' }) {
  return (
    <article className={`admin-usage-metric admin-usage-metric--${tone}`}>
      <span className="admin-usage-metric__icon" aria-hidden="true">{icon}</span>
      <div>
        <strong title={String(value)}>{formatNumber(value)}</strong>
        <span>{label}</span>
        <small>{detail}</small>
      </div>
    </article>
  );
}

export default function AdminUsagePanel({ token, onUnauthorized }) {
  const [days, setDays] = useState(30);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');

  const loadUsage = useCallback(async ({ signal, silent = false } = {}) => {
    if (silent) setRefreshing(true);
    else setLoading(true);
    setError('');
    try {
      setReport(await getAdminUsage(token, days, signal));
    } catch (requestError) {
      if (requestError.name === 'AbortError') return;
      if (requestError.status === 401) {
        onUnauthorized();
        return;
      }
      setError(requestError.message || 'Não foi possível carregar o consumo do agente.');
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [days, onUnauthorized, token]);

  useEffect(() => {
    const controller = new AbortController();
    loadUsage({ signal: controller.signal });
    return () => controller.abort();
  }, [loadUsage]);

  const totals = report?.totals || EMPTY_TOTALS;
  const users = report?.users || [];
  const generationAverage = totals.generated_responses
    ? Math.round(totals.total_tokens / totals.generated_responses)
    : 0;
  const llmRequests = totals.generated_responses + totals.cache_hits;
  const cacheRate = llmRequests ? Math.round((totals.cache_hits / llmRequests) * 100) : 0;

  return (
    <section className="admin-usage" aria-labelledby="usage-title">
      <div className="admin-usage__head">
        <div className="admin-section-heading">
          <span className="admin-section-heading__index">03</span>
          <div>
            <h2 id="usage-title">Consumo do agente</h2>
            <p>Tokens reportados pelo provedor, associados ao usuário autenticado.</p>
          </div>
        </div>
        <div className="admin-usage__controls">
          <div className="admin-periods" aria-label="Período do consumo">
            {PERIODS.map((period) => (
              <button
                key={period.value}
                type="button"
                className={days === period.value ? 'is-active' : ''}
                onClick={() => setDays(period.value)}
                aria-pressed={days === period.value}
              >
                {period.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="admin-icon-button"
            onClick={() => loadUsage({ silent: true })}
            disabled={refreshing}
            aria-label="Atualizar consumo"
            title="Atualizar consumo"
          >
            <RefreshCw size={15} className={refreshing ? 'admin-spin' : ''} />
          </button>
        </div>
      </div>

      {error ? (
        <div className="admin-usage__state" role="alert">
          <DatabaseZap size={23} />
          <strong>TELEMETRIA INDISPONÍVEL</strong>
          <span>{error}</span>
          <button type="button" className="admin-button admin-button--quiet" onClick={() => loadUsage()}>
            TENTAR NOVAMENTE
          </button>
        </div>
      ) : loading ? (
        <div className="admin-usage__loading" aria-label="Carregando consumo">
          {Array.from({ length: 4 }, (_, index) => <span key={index} className="skeleton" />)}
        </div>
      ) : (
        <>
          <div className="admin-usage__metrics">
            <UsageMetric
              icon={<Activity size={18} />}
              value={totals.total_tokens}
              label="TOKENS CONSUMIDOS"
              detail={`${formatNumber(generationAverage)} / geração em média`}
            />
            <UsageMetric
              icon={<ArrowDownToLine size={18} />}
              value={totals.input_tokens}
              label="TOKENS DE ENTRADA"
              detail={`${formatNumber(totals.cached_tokens)} vieram do cache OpenAI`}
              tone="purple"
            />
            <UsageMetric
              icon={<ArrowUpFromLine size={18} />}
              value={totals.output_tokens}
              label="TOKENS DE SAÍDA"
              detail={`${formatNumber(totals.reasoning_tokens)} de raciocínio inclusos`}
              tone="orange"
            />
            <UsageMetric
              icon={<Sparkles size={18} />}
              value={totals.generated_responses}
              label="GERAÇÕES LLM"
              detail={`${cacheRate}% das respostas LLM reutilizadas`}
              tone="green"
            />
          </div>

          <div className="admin-usage-table-scroll">
            <table className="admin-usage-table">
              <thead>
                <tr>
                  <th>IDENTIDADE</th>
                  <th>TOTAL</th>
                  <th>ENTRADA</th>
                  <th>SAÍDA</th>
                  <th>GERAÇÕES</th>
                  <th>CACHE HIT</th>
                  <th>POUPADOS</th>
                </tr>
              </thead>
              <tbody>
                {users.map((item) => (
                  <tr key={item.id}>
                    <td data-label="IDENTIDADE">
                      <div className="admin-usage-identity">
                        <span>{item.email.slice(0, 1).toUpperCase()}</span>
                        <div><strong>{item.email}</strong><small>{item.role === 'admin' ? 'ADMINISTRADOR' : 'MEMBRO'} · {STATUS_LABELS[item.status] || item.status.toUpperCase()}</small></div>
                      </div>
                    </td>
                    <td data-label="TOTAL"><strong className="admin-token-total">{formatNumber(item.total_tokens)}</strong></td>
                    <td data-label="ENTRADA">{formatNumber(item.input_tokens)}</td>
                    <td data-label="SAÍDA">{formatNumber(item.output_tokens)}</td>
                    <td data-label="GERAÇÕES">{formatNumber(item.generated_responses)}</td>
                    <td data-label="CACHE HIT">{formatNumber(item.cache_hits)}</td>
                    <td data-label="POUPADOS" className="admin-token-saved">{formatNumber(item.saved_tokens)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="admin-usage__note">
            <ShieldCheck size={13} />
            <span>
              Contagem iniciada em <strong>{formatDate(report?.tracking_since)}</strong>. Cache interno custa zero tokens na nova requisição;
              tokens de raciocínio já estão incluídos na saída. Nenhum prompt ou resposta é salvo nesta telemetria.
            </span>
          </div>
        </>
      )}
    </section>
  );
}
