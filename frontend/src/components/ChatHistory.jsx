import { useDeferredValue, useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  Check,
  MessageSquareText,
  Pencil,
  Pin,
  Plus,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import { CHAT_API_BASE } from '../hooks/useChatAuth';

function parseDate(value) {
  const parsed = value ? new Date(value) : null;
  return parsed && !Number.isNaN(parsed.getTime()) ? parsed : new Date(0);
}

function dayStart(value) {
  const date = new Date(value);
  date.setHours(0, 0, 0, 0);
  return date.getTime();
}

function groupConversations(items) {
  const today = dayStart(Date.now());
  const day = 86_400_000;
  const groups = [
    { id: 'pinned', label: 'FIXADAS', items: items.filter((item) => item.pinned) },
    { id: 'today', label: 'HOJE', items: [] },
    { id: 'yesterday', label: 'ONTEM', items: [] },
    { id: 'week', label: 'ÚLTIMOS 7 DIAS', items: [] },
    { id: 'older', label: 'MAIS ANTIGAS', items: [] },
  ];
  items.filter((item) => !item.pinned).forEach((item) => {
    const difference = today - dayStart(parseDate(item.updated_at));
    if (difference <= 0) groups[1].items.push(item);
    else if (difference <= day) groups[2].items.push(item);
    else if (difference <= day * 7) groups[3].items.push(item);
    else groups[4].items.push(item);
  });
  return groups.filter((group) => group.items.length > 0);
}

function formatUpdatedAt(value) {
  return parseDate(value).toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function ChatHistory({
  token,
  activeConversationId,
  onBack,
  onNew,
  onSelect,
}) {
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);
  const [conversations, setConversations] = useState([]);
  const [state, setState] = useState('loading');
  const [editingId, setEditingId] = useState(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  const editRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    const search = new URLSearchParams();
    if (deferredQuery.trim()) search.set('q', deferredQuery.trim());
    fetch(`${CHAT_API_BASE}/chat/conversations?${search}`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(async (response) => {
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || 'Falha ao carregar conversas.');
        setConversations(Array.isArray(body.conversations) ? body.conversations : []);
        setState('ready');
      })
      .catch((error) => {
        if (error.name !== 'AbortError') setState('error');
      });
    return () => controller.abort();
  }, [deferredQuery, token]);

  useEffect(() => {
    if (editingId) editRef.current?.focus();
  }, [editingId]);

  async function patchConversation(id, patch) {
    const response = await fetch(`${CHAT_API_BASE}/chat/conversations/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(patch),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.detail || 'Não foi possível atualizar a conversa.');
    setConversations((current) => current
      .map((item) => (item.id === id ? { ...item, ...body } : item))
      .toSorted((left, right) => Number(right.pinned) - Number(left.pinned)
        || parseDate(right.updated_at) - parseDate(left.updated_at)));
  }

  async function togglePinned(item) {
    const pinned = !item.pinned;
    setConversations((current) => current.map((conversation) => (
      conversation.id === item.id ? { ...conversation, pinned } : conversation
    )));
    try {
      await patchConversation(item.id, { pinned });
    } catch {
      setConversations((current) => current.map((conversation) => (
        conversation.id === item.id ? { ...conversation, pinned: item.pinned } : conversation
      )));
    }
  }

  async function saveTitle(item) {
    const title = editingTitle.trim();
    if (!title) return;
    try {
      await patchConversation(item.id, { title });
      setEditingId(null);
    } catch {
      editRef.current?.focus();
    }
  }

  async function deleteConversation(id) {
    const response = await fetch(`${CHAT_API_BASE}/chat/conversations/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) return;
    setConversations((current) => current.filter((item) => item.id !== id));
    setDeletingId(null);
    if (id === activeConversationId) onNew();
  }

  const groups = groupConversations(conversations);

  return (
    <section className="chat-history" aria-label="Histórico de conversas">
      <div className="chat-history__heading">
        <button type="button" onClick={onBack} aria-label="Voltar para a conversa">
          <ArrowLeft size={15} />
        </button>
        <div>
          <strong>CONVERSAS</strong>
          <small>{conversations.length} NO ARQUIVO ATUAL</small>
        </div>
        <button type="button" onClick={onNew} aria-label="Nova conversa">
          <Plus size={16} />
        </button>
      </div>

      <label className="chat-history__search">
        <Search size={14} aria-hidden="true" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar título ou conteúdo…"
          aria-label="Buscar conversas"
        />
        {query ? (
          <button type="button" onClick={() => setQuery('')} aria-label="Limpar busca">
            <X size={13} />
          </button>
        ) : null}
      </label>

      <div className="chat-history__list">
        {state === 'loading' ? (
          <div className="chat-history__state"><i /> INDEXANDO CONVERSAS…</div>
        ) : null}
        {state === 'error' ? (
          <div className="chat-history__empty">
            <MessageSquareText size={24} />
            <strong>Arquivo indisponível</strong>
            <span>Não foi possível consultar o histórico persistente.</span>
          </div>
        ) : null}
        {state === 'ready' && groups.length === 0 ? (
          <div className="chat-history__empty">
            <MessageSquareText size={24} />
            <strong>{query ? 'Nenhum resultado' : 'Nenhuma conversa arquivada'}</strong>
            <span>{query ? 'Tente buscar por outro termo.' : 'Sua próxima análise aparecerá aqui.'}</span>
          </div>
        ) : null}

        {state === 'ready' ? groups.map((group) => (
          <div className="chat-history__group" key={group.id}>
            <div className="chat-history__group-label">
              <span>{group.label}</span><i />
            </div>
            {group.items.map((item) => (
              <article
                key={item.id}
                className={`chat-thread ${item.id === activeConversationId ? 'chat-thread--active' : ''}`}
              >
                <div className="chat-thread__main">
                  <span className="chat-thread__mark" aria-hidden="true">
                    <MessageSquareText size={14} />
                  </span>
                  <span className="chat-thread__content">
                    {editingId === item.id ? (
                      <span className="chat-thread__edit" onClick={(event) => event.stopPropagation()}>
                        <input
                          ref={editRef}
                          value={editingTitle}
                          maxLength={120}
                          onChange={(event) => setEditingTitle(event.target.value)}
                          onKeyDown={(event) => {
                            if (event.key === 'Enter') saveTitle(item);
                            if (event.key === 'Escape') setEditingId(null);
                          }}
                          aria-label="Novo título da conversa"
                        />
                        <button type="button" onClick={() => saveTitle(item)} aria-label="Salvar título">
                          <Check size={12} />
                        </button>
                        <button type="button" onClick={() => setEditingId(null)} aria-label="Cancelar edição">
                          <X size={12} />
                        </button>
                      </span>
                    ) : (
                      <button className="chat-thread__select" type="button" onClick={() => onSelect(item)}>
                        <strong>{item.title}</strong>
                        <span className="chat-thread__preview">{item.preview}</span>
                        <span className="chat-thread__meta">
                          <b>{item.origin_label || 'DASHBOARD'}</b>
                          <span>{formatUpdatedAt(item.updated_at)}</span>
                          <span>{item.message_count} msgs</span>
                        </span>
                      </button>
                    )}
                  </span>
                </div>

                {deletingId === item.id ? (
                  <div className="chat-thread__confirm">
                    <span>EXCLUIR?</span>
                    <button type="button" onClick={() => deleteConversation(item.id)}>SIM</button>
                    <button type="button" onClick={() => setDeletingId(null)}>NÃO</button>
                  </div>
                ) : (
                  <div className="chat-thread__actions">
                    <button
                      type="button"
                      className={item.pinned ? 'chat-thread__action--active' : ''}
                      onClick={() => togglePinned(item)}
                      aria-label={item.pinned ? 'Desafixar conversa' : 'Fixar conversa'}
                    >
                      <Pin size={12} />
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditingId(item.id);
                        setEditingTitle(item.title);
                      }}
                      aria-label="Renomear conversa"
                    >
                      <Pencil size={12} />
                    </button>
                    <button type="button" onClick={() => setDeletingId(item.id)} aria-label="Excluir conversa">
                      <Trash2 size={12} />
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        )) : null}
      </div>
    </section>
  );
}
