import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  ClipboardCheck,
  LoaderCircle,
  Plus,
  RefreshCw,
  ShieldAlert,
  UserRound,
  XCircle,
} from 'lucide-react';
import { useChatAuth } from '../hooks/useChatAuth';
import {
  createOperationalAlert,
  getOperationalModelSources,
  listOperationalAlerts,
  updateOperationalAlert,
} from '../services/operations';
import './OperationsPage.css';

const STATUS = {
  new: { label: 'NOVO', tone: 'new' },
  acknowledged: { label: 'RECONHECIDO', tone: 'acknowledged' },
  investigating: { label: 'EM INVESTIGAÇÃO', tone: 'investigating' },
  resolved: { label: 'CONCLUÍDO', tone: 'resolved' },
  false_positive: { label: 'FALSO POSITIVO', tone: 'false-positive' },
};

const EMPTY_FORM = {
  title: '', incident_ref: '', priority: 'P2', source_model_id: 'manual',
  risk_score: '', team: '', assignee_email: '', recommended_action: '',
};

function formatDate(value) {
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '—';
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  }).format(parsed).replace('.', '').toUpperCase();
}

function StatusBadge({ status }) {
  const item = STATUS[status] || STATUS.new;
  return <span className={`ops-status ops-status--${item.tone}`}><i />{item.label}</span>;
}

function Summary({ icon, value, label, tone }) {
  return (
    <article className={`ops-summary ops-summary--${tone || 'neutral'}`}>
      <span>{icon}</span><div><strong>{value}</strong><small>{label}</small></div>
    </article>
  );
}

function AlertCard({ alert, busy, onSave }) {
  const [draft, setDraft] = useState(() => ({
    status: alert.status,
    team: alert.team || '',
    assignee_email: alert.assignee_email || '',
    recommended_action: alert.recommended_action || '',
    action_taken: alert.action_taken || '',
    observed_result: alert.observed_result || '',
  }));
  const change = (field) => (event) => setDraft((current) => ({
    ...current, [field]: event.target.value,
  }));
  const closed = ['resolved', 'false_positive'].includes(draft.status);

  return (
    <article className={`ops-card ops-card--${alert.priority.toLowerCase()}`}>
      <header>
        <div className="ops-card__identity">
          <span>{alert.priority}</span>
          <div>
            <strong>{alert.title}</strong>
            <small>{alert.incident_ref || 'SEM REFERÊNCIA ITSM'} · ATUALIZADO {formatDate(alert.updated_at)}</small>
          </div>
        </div>
        <StatusBadge status={alert.status} />
      </header>

      <div className="ops-card__evidence">
        <span>ORIGEM <strong>{alert.source_model_id}</strong></span>
        <span>SCORE <strong>{alert.risk_score == null ? 'NÃO INFORMADO' : `${(alert.risk_score * 100).toFixed(1)}%`}</strong></span>
        <span>VERSÃO <strong>#{alert.version}</strong></span>
      </div>
      {alert.risk_score != null ? (
        <p className="ops-card__disclaimer">Score de ranking para triagem; não representa probabilidade calibrada.</p>
      ) : null}

      <div className="ops-card__workflow">
        <label>
          <span>STATUS</span>
          <div className="ops-select"><select value={draft.status} onChange={change('status')}>
            {Object.entries(STATUS).map(([value, item]) => <option key={value} value={value}>{item.label}</option>)}
          </select><ChevronDown size={13} /></div>
        </label>
        <label><span>TIME</span><input value={draft.team} onChange={change('team')} placeholder="Ex.: Team07" /></label>
        <label><span>RESPONSÁVEL</span><input type="email" value={draft.assignee_email} onChange={change('assignee_email')} placeholder="analista@empresa.com" /></label>
      </div>

      <div className="ops-card__notes">
        <label><span>AÇÃO RECOMENDADA</span><textarea rows="2" value={draft.recommended_action} onChange={change('recommended_action')} placeholder="Próximo passo sugerido e evidência necessária" /></label>
        <label><span>AÇÃO TOMADA {closed ? '*' : ''}</span><textarea rows="2" value={draft.action_taken} onChange={change('action_taken')} placeholder="O que foi executado durante a investigação" /></label>
        <label><span>RESULTADO OBSERVADO {closed ? '*' : ''}</span><textarea rows="2" value={draft.observed_result} onChange={change('observed_result')} placeholder="Resultado, falso positivo ou aprendizado para o modelo" /></label>
      </div>

      <footer>
        <span>CRIADO POR {alert.created_by}</span>
        <button type="button" onClick={() => onSave(alert, draft)} disabled={busy}>
          {busy ? <LoaderCircle size={14} className="ops-spin" /> : <ClipboardCheck size={14} />}
          SALVAR EVOLUÇÃO
        </button>
      </footer>
    </article>
  );
}

export default function OperationsPage() {
  const { user, logout } = useChatAuth();
  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState({ total: 0, by_status: {}, by_priority: {} });
  const [filters, setFilters] = useState({ status: '', priority: '' });
  const [form, setForm] = useState(EMPTY_FORM);
  const [modelSources, setModelSources] = useState([]);
  const [formOpen, setFormOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const load = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    try {
      const result = await listOperationalAlerts(user.token, filters, signal);
      setAlerts(Array.isArray(result.alerts) ? result.alerts : []);
      setSummary(result.summary || { total: 0, by_status: {}, by_priority: {} });
    } catch (requestError) {
      if (requestError.name === 'AbortError') return;
      if (requestError.status === 401) logout();
      else setError(requestError.message || 'Não foi possível carregar a fila.');
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [filters, logout, user.token]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    const controller = new AbortController();
    getOperationalModelSources(user.token, controller.signal)
      .then((registry) => setModelSources(
        (registry.models || []).filter((model) => model.task === 'ola_risk_triage'),
      ))
      .catch((requestError) => {
        if (requestError.name !== 'AbortError' && requestError.status === 401) logout();
      });
    return () => controller.abort();
  }, [logout, user.token]);

  const activeCount = useMemo(() => (
    (summary.by_status?.new || 0)
    + (summary.by_status?.acknowledged || 0)
    + (summary.by_status?.investigating || 0)
  ), [summary]);

  const updateForm = (field) => (event) => setForm((current) => ({
    ...current, [field]: event.target.value,
  }));

  async function handleCreate(event) {
    event.preventDefault();
    setCreating(true);
    setError('');
    try {
      await createOperationalAlert(user.token, {
        ...form,
        risk_score: form.risk_score === '' ? null : Number(form.risk_score),
      });
      setForm(EMPTY_FORM);
      setFormOpen(false);
      setNotice('Investigação adicionada à fila operacional.');
      await load();
    } catch (requestError) {
      if (requestError.status === 401) logout();
      else setError(requestError.message || 'Não foi possível criar a investigação.');
    } finally {
      setCreating(false);
    }
  }

  async function handleSave(alert, draft) {
    setBusyId(alert.id);
    setError('');
    try {
      const result = await updateOperationalAlert(user.token, alert.id, {
        ...draft,
        version: alert.version,
      });
      setAlerts((current) => current.map((item) => item.id === alert.id ? result.alert : item));
      setNotice('Evolução registrada e preservada na auditoria.');
      await load();
    } catch (requestError) {
      if (requestError.status === 401) logout();
      else {
        setError(requestError.message || 'Não foi possível atualizar a investigação.');
        if (requestError.status === 409) await load();
      }
    } finally {
      setBusyId('');
    }
  }

  return (
    <main className="ops-page page-enter">
      <header className="ops-header">
        <div><span>ALERTA → INVESTIGAÇÃO → RESULTADO</span><h1>Fila operacional</h1><p>Transforme sinais dos modelos em ações rastreáveis e feedback observado.</p></div>
        <button type="button" onClick={() => setFormOpen((current) => !current)}><Plus size={15} /> NOVA INVESTIGAÇÃO</button>
      </header>

      <div className="ops-content">
        <section className="ops-summaries" aria-label="Resumo da fila">
          <Summary icon={<Activity size={18} />} value={summary.total || 0} label="REGISTROS" />
          <Summary icon={<ShieldAlert size={18} />} value={activeCount} label="EM ABERTO" tone="warning" />
          <Summary icon={<CheckCircle2 size={18} />} value={summary.by_status?.resolved || 0} label="CONCLUÍDOS" tone="healthy" />
          <Summary icon={<XCircle size={18} />} value={summary.by_status?.false_positive || 0} label="FALSOS POSITIVOS" tone="muted" />
        </section>

        {formOpen ? (
          <form className="ops-create" onSubmit={handleCreate}>
            <header><div><span>01</span><h2>Registrar investigação</h2></div><p>Não invente identificadores: a referência ITSM é opcional até existir integração.</p></header>
            <div className="ops-create__grid">
              <label className="ops-field ops-field--wide"><span>TÍTULO *</span><input required minLength="4" value={form.title} onChange={updateForm('title')} placeholder="Descreva o sinal que exige investigação" /></label>
              <label className="ops-field"><span>REFERÊNCIA ITSM</span><input value={form.incident_ref} onChange={updateForm('incident_ref')} placeholder="INC000000" /></label>
              <label className="ops-field"><span>PRIORIDADE</span><div className="ops-select"><select value={form.priority} onChange={updateForm('priority')}><option>P2</option><option>P3</option></select><ChevronDown size={13} /></div></label>
              <label className="ops-field"><span>ORIGEM</span><div className="ops-select"><select value={form.source_model_id} onChange={updateForm('source_model_id')}><option value="manual">TRIAGEM MANUAL</option>{modelSources.map((model) => <option key={model.id} value={model.id}>{model.display_name.toUpperCase()} · {model.status.toUpperCase()}</option>)}</select><ChevronDown size={13} /></div></label>
              <label className="ops-field"><span>SCORE 0–1</span><input type="number" min="0" max="1" step="0.0001" value={form.risk_score} onChange={updateForm('risk_score')} placeholder="Opcional" /></label>
              <label className="ops-field"><span>TIME</span><input value={form.team} onChange={updateForm('team')} placeholder="Ex.: Team07" /></label>
              <label className="ops-field"><span>RESPONSÁVEL</span><input type="email" value={form.assignee_email} onChange={updateForm('assignee_email')} placeholder="analista@empresa.com" /></label>
              <label className="ops-field ops-field--full"><span>AÇÃO RECOMENDADA</span><textarea rows="3" value={form.recommended_action} onChange={updateForm('recommended_action')} placeholder="Evidência a validar, próximo passo e gatilho de escalação" /></label>
            </div>
            <footer><button type="button" onClick={() => setFormOpen(false)}>CANCELAR</button><button type="submit" disabled={creating}>{creating ? <LoaderCircle size={14} className="ops-spin" /> : <Plus size={14} />} ADICIONAR À FILA</button></footer>
          </form>
        ) : null}

        <section className="ops-board">
          <header className="ops-board__head">
            <div><span>02</span><div><h2>Investigações</h2><p>Resultado observado é obrigatório para fechar o ciclo.</p></div></div>
            <div className="ops-filters">
              <label><span className="sr-only">Filtrar prioridade</span><select value={filters.priority} onChange={(event) => setFilters((current) => ({ ...current, priority: event.target.value }))}><option value="">P2 + P3</option><option>P2</option><option>P3</option></select><ChevronDown size={13} /></label>
              <label><span className="sr-only">Filtrar status</span><select value={filters.status} onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}><option value="">TODOS OS STATUS</option>{Object.entries(STATUS).map(([value, item]) => <option key={value} value={value}>{item.label}</option>)}</select><ChevronDown size={13} /></label>
              <button type="button" onClick={() => load()} aria-label="Atualizar fila"><RefreshCw size={14} /></button>
            </div>
          </header>

          {error ? <div className="ops-state ops-state--error" role="alert"><AlertTriangle size={24} /><strong>CONSULTA NÃO CONCLUÍDA</strong><p>{error}</p><button type="button" onClick={() => load()}>TENTAR NOVAMENTE</button></div>
            : loading ? <div className="ops-loading">{[0, 1, 2].map((item) => <span className="skeleton" key={item} />)}</div>
              : alerts.length === 0 ? <div className="ops-state"><CircleDot size={25} /><strong>FILA SEM REGISTROS</strong><p>Crie uma investigação manual ou registre um alerta shadow. Nenhum incidente será inventado automaticamente.</p><button type="button" onClick={() => setFormOpen(true)}>CRIAR PRIMEIRA INVESTIGAÇÃO</button></div>
                : <div className="ops-list">{alerts.map((alert) => <AlertCard key={`${alert.id}:${alert.version}`} alert={alert} busy={busyId === alert.id} onSave={handleSave} />)}</div>}
        </section>

        <aside className="ops-governance"><UserRound size={14} /><span><strong>RESPONSABILIDADE HUMANA</strong> Modelos priorizam a fila; a equipe valida, executa e registra o resultado. Shadow mode não dispara ação automática.</span></aside>
      </div>

      {notice ? <div className="ops-toast" role="status"><CheckCircle2 size={15} />{notice}<button type="button" onClick={() => setNotice('')}>×</button></div> : null}
    </main>
  );
}
