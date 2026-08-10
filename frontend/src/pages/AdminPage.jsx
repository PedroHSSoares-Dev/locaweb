import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  Check,
  ChevronDown,
  Clock3,
  KeyRound,
  LoaderCircle,
  MailPlus,
  RefreshCw,
  Search,
  ShieldCheck,
  ShieldOff,
  Trash2,
  UserCheck,
  Users,
  X,
} from 'lucide-react';
import { useChatAuth } from '../hooks/useChatAuth';
import AdminUsagePanel from '../components/AdminUsagePanel';
import {
  createAdminUser,
  deleteAdminUser,
  listAdminUsers,
  updateAdminUser,
} from '../services/adminUsers';
import './AdminPage.css';

const ROLE_LABEL = { admin: 'ADMINISTRADOR', member: 'MEMBRO' };
const STATUS_LABEL = { pending: 'PENDENTE', active: 'ATIVO', disabled: 'DESATIVADO' };
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function normalizeUser(item) {
  return {
    id: item.id || item.user_id || item.email,
    email: String(item.email || '').toLowerCase(),
    role: item.role === 'admin' ? 'admin' : 'member',
    status: ['pending', 'active', 'disabled'].includes(item.status) ? item.status : 'pending',
    createdAt: item.created_at || item.createdAt,
    lastLoginAt: item.last_login_at || item.lastLoginAt,
    invitedBy: item.invited_by || item.invitedBy,
    isOwner: Boolean(item.is_owner ?? item.isOwner),
    version: item.version,
  };
}

function formatDate(value, empty = 'AINDA NÃO ACESSOU') {
  if (!value) return empty;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return empty;
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date).replace('.', '').toUpperCase();
}

function StatusBadge({ status }) {
  return (
    <span className={`admin-status admin-status--${status}`}>
      <span aria-hidden="true" />
      {STATUS_LABEL[status] || status}
    </span>
  );
}

function SummaryTile({ icon, value, label, tone = 'neutral', delay }) {
  return (
    <article className={`admin-summary admin-summary--${tone}`} style={{ '--delay': delay }}>
      <span className="admin-summary__icon" aria-hidden="true">{icon}</span>
      <div>
        <strong>{value}</strong>
        <span>{label}</span>
      </div>
    </article>
  );
}

function ConfirmDialog({ action, busy, onCancel, onConfirm }) {
  const confirmRef = useRef(null);

  useEffect(() => {
    if (!action) return undefined;
    confirmRef.current?.focus();
    const onKeyDown = (event) => {
      if (event.key === 'Escape' && !busy) onCancel();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [action, busy, onCancel]);

  if (!action) return null;
  const removing = action.type === 'remove';
  const disabling = action.type === 'disable';
  const verb = removing ? 'REMOVER ACESSO' : disabling ? 'DESATIVAR ACESSO' : 'REATIVAR ACESSO';

  return (
    <div className="admin-dialog-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget && !busy) onCancel();
    }}>
      <section
        className="admin-dialog"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="admin-dialog-title"
        aria-describedby="admin-dialog-description"
      >
        <span className={`admin-dialog__icon${removing || disabling ? ' admin-dialog__icon--danger' : ''}`}>
          {removing ? <Trash2 size={21} /> : disabling ? <ShieldOff size={21} /> : <ShieldCheck size={21} />}
        </span>
        <div className="admin-dialog__signal">CONFIRMAÇÃO DE SEGURANÇA</div>
        <h2 id="admin-dialog-title">{verb}</h2>
        <p id="admin-dialog-description">
          {removing
            ? 'O acesso será removido e as sessões existentes serão invalidadas. O histórico de auditoria será preservado.'
            : disabling
              ? 'Sessões válidas desse usuário deixarão de autorizar novos acessos.'
              : 'O usuário voltará a conseguir entrar com a identidade Microsoft vinculada.'}
        </p>
        <code>{action.user.email}</code>
        <div className="admin-dialog__actions">
          <button type="button" className="admin-button admin-button--quiet" onClick={onCancel} disabled={busy}>
            CANCELAR
          </button>
          <button
            ref={confirmRef}
            type="button"
            className={`admin-button ${removing || disabling ? 'admin-button--danger' : 'admin-button--primary'}`}
            onClick={onConfirm}
            disabled={busy}
          >
            {busy ? <LoaderCircle size={14} className="admin-spin" /> : null}
            {verb}
          </button>
        </div>
      </section>
    </div>
  );
}

export default function AdminPage() {
  const { user: sessionUser, logout } = useChatAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [notice, setNotice] = useState(null);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [roleFilter, setRoleFilter] = useState('all');
  const [email, setEmail] = useState('');
  const [newRole, setNewRole] = useState('member');
  const [formError, setFormError] = useState('');
  const [creating, setCreating] = useState(false);
  const [activeMutation, setActiveMutation] = useState('');
  const [confirmAction, setConfirmAction] = useState(null);
  const noticeTimer = useRef(null);

  const showNotice = useCallback((message, tone = 'success') => {
    window.clearTimeout(noticeTimer.current);
    setNotice({ message, tone });
    noticeTimer.current = window.setTimeout(() => setNotice(null), 5_000);
  }, []);

  useEffect(() => () => window.clearTimeout(noticeTimer.current), []);

  const handleApiError = useCallback((error, fallback) => {
    if (error.status === 401) {
      logout();
      return;
    }
    showNotice(error.message || fallback, 'error');
  }, [logout, showNotice]);

  const loadUsers = useCallback(async ({ signal, silent = false } = {}) => {
    if (silent) setRefreshing(true);
    else setLoading(true);
    setLoadError('');
    try {
      const items = await listAdminUsers(sessionUser.token, signal);
      setUsers(items.map(normalizeUser));
    } catch (error) {
      if (error.name === 'AbortError') return;
      if (error.status === 401) {
        logout();
        return;
      }
      setLoadError(error.message || 'Não foi possível carregar os acessos.');
    } finally {
      if (!signal?.aborted) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [logout, sessionUser.token]);

  useEffect(() => {
    const controller = new AbortController();
    loadUsers({ signal: controller.signal });
    return () => controller.abort();
  }, [loadUsers]);

  const counts = useMemo(() => users.reduce((acc, item) => {
    acc[item.status] = (acc[item.status] || 0) + 1;
    if (item.role === 'admin') acc.admin += 1;
    return acc;
  }, { active: 0, pending: 0, disabled: 0, admin: 0 }), [users]);

  const filteredUsers = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return users.filter((item) => (
      (!normalizedQuery || item.email.includes(normalizedQuery))
      && (statusFilter === 'all' || item.status === statusFilter)
      && (roleFilter === 'all' || item.role === roleFilter)
    ));
  }, [query, roleFilter, statusFilter, users]);

  async function handleCreate(event) {
    event.preventDefault();
    const normalizedEmail = email.trim().toLowerCase();
    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      setFormError('INFORME UM E-MAIL VÁLIDO');
      return;
    }
    if (users.some((item) => item.email === normalizedEmail)) {
      setFormError('ESTE E-MAIL JÁ POSSUI UM CADASTRO');
      return;
    }
    setCreating(true);
    setFormError('');
    try {
      await createAdminUser(sessionUser.token, { email: normalizedEmail, role: newRole });
      setEmail('');
      setNewRole('member');
      showNotice(`Acesso preparado para ${normalizedEmail}.`);
      await loadUsers({ silent: true });
    } catch (error) {
      if (error.status === 401) logout();
      else setFormError(error.message || 'NÃO FOI POSSÍVEL CRIAR O ACESSO');
    } finally {
      setCreating(false);
    }
  }

  async function handleRoleChange(item, role) {
    if (role === item.role) return;
    setActiveMutation(`role:${item.id}`);
    try {
      const updated = await updateAdminUser(sessionUser.token, item.id, { role, version: item.version });
      setUsers((current) => current.map((entry) => (
        entry.id === item.id ? normalizeUser(updated.user || updated) : entry
      )));
      showNotice(`${item.email} agora é ${ROLE_LABEL[role].toLowerCase()}.`);
    } catch (error) {
      if (error.status === 409) await loadUsers({ silent: true });
      handleApiError(error, 'Não foi possível alterar a permissão.');
    } finally {
      setActiveMutation('');
    }
  }

  async function handleConfirmedAction() {
    if (!confirmAction) return;
    const { type, user: item } = confirmAction;
    setActiveMutation(`${type}:${item.id}`);
    try {
      if (type === 'remove') {
        const updated = await deleteAdminUser(sessionUser.token, item.id, item.version);
        setUsers((current) => current.map((entry) => (
          entry.id === item.id ? normalizeUser(updated.user || { ...entry, status: 'disabled' }) : entry
        )));
        showNotice(`Acesso de ${item.email} removido; histórico preservado.`);
      } else {
        const status = type === 'disable' ? 'disabled' : 'active';
        const updated = await updateAdminUser(sessionUser.token, item.id, { status, version: item.version });
        setUsers((current) => current.map((entry) => (
          entry.id === item.id ? normalizeUser(updated.user || updated) : entry
        )));
        showNotice(`${item.email} foi ${status === 'active' ? 'reativado' : 'desativado'}.`);
      }
      setConfirmAction(null);
    } catch (error) {
      if (error.status === 409) await loadUsers({ silent: true });
      handleApiError(error, 'Não foi possível concluir a operação.');
    } finally {
      setActiveMutation('');
    }
  }

  const hasFilters = query || statusFilter !== 'all' || roleFilter !== 'all';

  return (
    <main className="admin-page page-enter">
      <header className="admin-header">
        <div>
          <div className="admin-header__eyebrow"><KeyRound size={13} /> CONTROLE DE ACESSO / DIRETÓRIO</div>
          <h1>Administração</h1>
          <p>Autorize identidades Microsoft, governe privilégios e acompanhe o uso do agente.</p>
        </div>
        <div className="admin-header__identity">
          <span>OPERADOR AUTORIZADO</span>
          <strong>{sessionUser.email}</strong>
          <small><ShieldCheck size={11} /> ADMIN</small>
        </div>
      </header>

      <div className="admin-content">
        <section className="admin-summaries" aria-label="Resumo dos acessos">
          <SummaryTile icon={<Users size={19} />} value={users.length} label="IDENTIDADES" delay="0ms" />
          <SummaryTile icon={<UserCheck size={19} />} value={counts.active} label="ACESSOS ATIVOS" tone="healthy" delay="45ms" />
          <SummaryTile icon={<Clock3 size={19} />} value={counts.pending} label="PENDENTES" tone="pending" delay="90ms" />
          <SummaryTile icon={<ShieldCheck size={19} />} value={counts.admin} label="ADMINISTRADORES" tone="admin" delay="135ms" />
        </section>

        <section className="admin-invite" aria-labelledby="invite-title">
          <div className="admin-section-heading">
            <span className="admin-section-heading__index">01</span>
            <div>
              <h2 id="invite-title">Criar acesso</h2>
              <p>O usuário será validado pelo Microsoft Entra ID no primeiro login.</p>
            </div>
          </div>
          <form className="admin-invite__form" onSubmit={handleCreate} noValidate>
            <label className="admin-field admin-field--email">
              <span>E-MAIL MICROSOFT AUTORIZADO</span>
              <div>
                <MailPlus size={16} aria-hidden="true" />
                <input
                  type="email"
                  value={email}
                  onChange={(event) => {
                    setEmail(event.target.value);
                    setFormError('');
                  }}
                  placeholder="usuario@empresa.com"
                  autoComplete="email"
                  aria-invalid={Boolean(formError)}
                  aria-describedby={formError ? 'admin-form-error' : undefined}
                />
              </div>
            </label>
            <fieldset className="admin-role-picker">
              <legend>PERMISSÃO INICIAL</legend>
              <label>
                <input type="radio" name="new-role" value="member" checked={newRole === 'member'} onChange={() => setNewRole('member')} />
                <span><strong>MEMBRO</strong><small>Dashboards e agente</small></span>
              </label>
              <label>
                <input type="radio" name="new-role" value="admin" checked={newRole === 'admin'} onChange={() => setNewRole('admin')} />
                <span><strong>ADMIN</strong><small>Gerencia acessos</small></span>
              </label>
            </fieldset>
            <button className="admin-button admin-button--primary admin-invite__submit" type="submit" disabled={creating}>
              {creating ? <LoaderCircle size={15} className="admin-spin" /> : <MailPlus size={15} />}
              {creating ? 'CRIANDO ACESSO…' : 'ADICIONAR À PLATAFORMA'}
            </button>
            {formError ? <p id="admin-form-error" className="admin-invite__error" role="alert"><AlertTriangle size={13} /> {formError}</p> : null}
          </form>
        </section>

        <section className="admin-directory" aria-labelledby="directory-title">
          <div className="admin-directory__head">
            <div className="admin-section-heading">
              <span className="admin-section-heading__index">02</span>
              <div>
                <h2 id="directory-title">Diretório autorizado</h2>
                <p>{filteredUsers.length} de {users.length} identidades visíveis</p>
              </div>
            </div>
            <button
              type="button"
              className="admin-icon-button"
              onClick={() => loadUsers({ silent: true })}
              disabled={refreshing}
              aria-label="Atualizar diretório"
              title="Atualizar diretório"
            >
              <RefreshCw size={15} className={refreshing ? 'admin-spin' : ''} />
            </button>
          </div>

          <div className="admin-filters">
            <label className="admin-search">
              <span className="sr-only">Buscar por e-mail</span>
              <Search size={15} aria-hidden="true" />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="BUSCAR POR E-MAIL…" />
              {query ? <button type="button" onClick={() => setQuery('')} aria-label="Limpar busca"><X size={14} /></button> : null}
            </label>
            <label className="admin-select">
              <span className="sr-only">Filtrar por status</span>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
                <option value="all">TODOS OS STATUS</option>
                <option value="active">ATIVOS</option>
                <option value="pending">PENDENTES</option>
                <option value="disabled">DESATIVADOS</option>
              </select>
              <ChevronDown size={13} aria-hidden="true" />
            </label>
            <label className="admin-select">
              <span className="sr-only">Filtrar por permissão</span>
              <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)}>
                <option value="all">TODAS AS PERMISSÕES</option>
                <option value="admin">ADMINISTRADORES</option>
                <option value="member">MEMBROS</option>
              </select>
              <ChevronDown size={13} aria-hidden="true" />
            </label>
          </div>

          {loadError ? (
            <div className="admin-state admin-state--error" role="alert">
              <AlertTriangle size={24} />
              <strong>FALHA AO CARREGAR DIRETÓRIO</strong>
              <p>{loadError}</p>
              <button type="button" className="admin-button admin-button--quiet" onClick={() => loadUsers()}>TENTAR NOVAMENTE</button>
            </div>
          ) : loading ? (
            <div className="admin-loading" aria-label="Carregando acessos">
              {Array.from({ length: 4 }, (_, index) => <span key={index} className="skeleton" />)}
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="admin-state">
              <Users size={25} />
              <strong>{hasFilters ? 'NENHUM RESULTADO' : 'DIRETÓRIO VAZIO'}</strong>
              <p>{hasFilters ? 'Ajuste os filtros para encontrar outra identidade.' : 'Crie o primeiro acesso usando o formulário acima.'}</p>
              {hasFilters ? <button type="button" className="admin-button admin-button--quiet" onClick={() => { setQuery(''); setStatusFilter('all'); setRoleFilter('all'); }}>LIMPAR FILTROS</button> : null}
            </div>
          ) : (
            <div className="admin-table-scroll">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>IDENTIDADE</th>
                    <th>STATUS</th>
                    <th>PERMISSÃO</th>
                    <th>ÚLTIMO ACESSO</th>
                    <th><span className="sr-only">Ações</span></th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((item) => {
                    const isSelf = item.email === sessionUser.email.toLowerCase();
                    const protectedAccount = isSelf || item.isOwner;
                    const mutating = activeMutation.endsWith(`:${item.id}`);
                    return (
                      <tr key={item.id}>
                        <td data-label="IDENTIDADE">
                          <div className="admin-identity-cell">
                            <span>{item.email.slice(0, 1).toUpperCase()}</span>
                            <div><strong>{item.email}</strong><small>CRIADO {formatDate(item.createdAt, '—')}</small></div>
                            {item.isOwner ? <em className="admin-owner-badge">PROPRIETÁRIO</em> : isSelf ? <em>VOCÊ</em> : null}
                          </div>
                        </td>
                        <td data-label="STATUS"><StatusBadge status={item.status} /></td>
                        <td data-label="PERMISSÃO">
                          <label className="admin-inline-select">
                            <span className="sr-only">Permissão de {item.email}</span>
                            <select
                              value={item.role}
                              onChange={(event) => handleRoleChange(item, event.target.value)}
                              disabled={mutating || protectedAccount}
                              title={item.isOwner ? 'O proprietário principal é protegido' : isSelf ? 'Sua própria permissão não pode ser alterada' : undefined}
                            >
                              <option value="member">MEMBRO</option>
                              <option value="admin">ADMINISTRADOR</option>
                            </select>
                            {mutating ? <LoaderCircle size={12} className="admin-spin" /> : <ChevronDown size={12} />}
                          </label>
                        </td>
                        <td data-label="ÚLTIMO ACESSO"><time className="admin-last-login">{formatDate(item.lastLoginAt)}</time></td>
                        <td data-label="AÇÕES">
                          <div className="admin-row-actions">
                            <button
                              type="button"
                              className={`admin-row-action ${item.status === 'disabled' ? 'admin-row-action--activate' : ''}`}
                              onClick={() => setConfirmAction({ type: item.status === 'disabled' ? 'enable' : 'disable', user: item })}
                              disabled={mutating || protectedAccount}
                              title={item.isOwner ? 'O proprietário principal não pode ser desativado' : isSelf ? 'Você não pode desativar seu próprio acesso' : item.status === 'disabled' ? 'Reativar acesso' : 'Desativar acesso'}
                              aria-label={`${item.status === 'disabled' ? 'Reativar' : 'Desativar'} acesso de ${item.email}`}
                            >
                              {item.status === 'disabled' ? <Check size={15} /> : <ShieldOff size={15} />}
                            </button>
                            <button
                              type="button"
                              className="admin-row-action admin-row-action--danger"
                              onClick={() => setConfirmAction({ type: 'remove', user: item })}
                              disabled={mutating || protectedAccount}
                              title={item.isOwner ? 'O proprietário principal não pode ser removido' : isSelf ? 'Você não pode remover seu próprio acesso' : 'Remover acesso'}
                              aria-label={`Remover acesso de ${item.email}`}
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <AdminUsagePanel token={sessionUser.token} onUnauthorized={logout} />

        <footer className="admin-footnote">
          <ShieldCheck size={13} />
          <span>A autenticação permanece no Microsoft Entra ID. Este diretório controla somente quem pode acessar o Predictfy e com qual privilégio.</span>
        </footer>
      </div>

      {notice ? (
        <div className={`admin-toast admin-toast--${notice.tone}`} role="status">
          {notice.tone === 'success' ? <Check size={15} /> : <AlertTriangle size={15} />}
          <span>{notice.message}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Fechar aviso"><X size={14} /></button>
        </div>
      ) : null}

      <ConfirmDialog
        action={confirmAction}
        busy={Boolean(activeMutation)}
        onCancel={() => setConfirmAction(null)}
        onConfirm={handleConfirmedAction}
      />
    </main>
  );
}
