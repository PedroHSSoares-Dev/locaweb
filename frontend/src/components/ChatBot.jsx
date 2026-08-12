import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  BrainCircuit,
  Gauge,
  History,
  PanelRightClose,
  Plus,
  SendHorizontal,
  ThumbsDown,
  ThumbsUp,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CHAT_API_BASE, useChatAuth } from '../hooks/useChatAuth';
import { useBreakpoint } from '../hooks/useBreakpoint';
import { useDashboard } from '../hooks/useDashboard';
import ChatHistory from './ChatHistory';
import './ChatBot.css';

const DEFAULT_WELCOME = 'SYSTEM READY. Contexto operacional 2023–2025 carregado. Como posso ajudar?';
const DEFAULT_SUGGESTIONS = ['Previsão amanhã', 'Status das metas', 'Cluster mais crítico'];
const ALLOWED_ACTION_ROUTES = new Set(['/gestao', '/monitoramento', '/operacoes', '/tecnico', '/modelos']);
const MAX_MESSAGE_LENGTH = 6000;
const PANEL_DEFAULT_WIDTH = 430;
const PANEL_MIN_WIDTH = 340;
const PANEL_MAX_WIDTH = 720;
const DASHBOARD_MIN_WIDTH = 620;
const DOCK_BREAKPOINT = 1180;
const ROUTE_LABELS = {
  '/gestao': 'GESTÃO',
  '/monitoramento': 'MONITORAMENTO',
  '/operacoes': 'FILA OPERACIONAL',
  '/tecnico': 'TÉCNICO',
  '/modelos': 'MODELOS',
  '/admin': 'ADMINISTRAÇÃO',
};

function clamp(value, minimum, maximum) {
  return Math.min(Math.max(value, minimum), maximum);
}

function panelPreferenceKey(email, preference) {
  return `predictfy_chat_panel:${email.toLowerCase()}:${preference}`;
}

function readPanelWidth(email) {
  try {
    const stored = Number(localStorage.getItem(panelPreferenceKey(email, 'width')));
    return Number.isFinite(stored)
      ? clamp(stored, PANEL_MIN_WIDTH, PANEL_MAX_WIDTH)
      : PANEL_DEFAULT_WIDTH;
  } catch {
    return PANEL_DEFAULT_WIDTH;
  }
}

function readPanelOpen(email) {
  try {
    const stored = localStorage.getItem(panelPreferenceKey(email, 'open'));
    return stored == null ? null : stored === 'true';
  } catch {
    return null;
  }
}

function AgentGlyph({ size = 28, active = false }) {
  return (
    <span
      className={`agent-glyph ${active ? 'agent-glyph--active' : ''}`}
      style={{ '--agent-glyph-size': `${size}px` }}
      aria-hidden="true"
    >
      <svg viewBox="0 0 32 32" fill="none">
        <path className="agent-glyph__frame" d="M16 2.75 27.25 9.2v13.6L16 29.25 4.75 22.8V9.2L16 2.75Z" />
        <path className="agent-glyph__signal" d="m9.2 22.4 6.65-14.1 6.9 14.1M12.25 16.45h7.55" />
        <circle className="agent-glyph__node" cx="15.85" cy="8.3" r="1.45" />
        <path className="agent-glyph__spark" d="M24.6 4.1v4.4M22.4 6.3h4.4" />
      </svg>
    </span>
  );
}

function readableErrorDetail(detail, fallback) {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (typeof item === 'string' ? item : item?.msg || item?.message))
      .filter(Boolean);
    if (messages.length > 0) return messages.join(' · ');
  }
  if (detail && typeof detail === 'object') {
    const message = detail.message || detail.msg || detail.error;
    if (typeof message === 'string' && message.trim()) return message;
  }
  return fallback;
}

function timeNow() {
  return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function timeFromIso(value) {
  const parsed = value ? new Date(value) : null;
  if (!parsed || Number.isNaN(parsed.getTime())) return timeNow();
  return parsed.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function contextKey(value) {
  if (!value) return '';
  const filters = Object.entries(value.filters || {}).toSorted(([left], [right]) => left.localeCompare(right));
  return JSON.stringify({ route: value.route, label: value.label, filters });
}

function formatElapsed(elapsedMs) {
  if (elapsedMs < 1000) return 'Worked for <1 sec';
  const totalSeconds = Math.max(1, Math.round(elapsedMs / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes > 0
    ? `Worked for ${minutes} min ${seconds} sec`
    : `Worked for ${seconds} sec`;
}

function conversationPreferenceKey(email) {
  return `predictfy_chat_conversation:${email.toLowerCase()}`;
}

function createConversationId() {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID().replaceAll('-', '');
  }
  return `conversation_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function readConversationId(email) {
  try {
    const stored = localStorage.getItem(conversationPreferenceKey(email));
    if (stored && /^[A-Za-z0-9_-]{1,64}$/.test(stored)) return stored;
    const created = createConversationId();
    localStorage.setItem(conversationPreferenceKey(email), created);
    return created;
  } catch {
    return createConversationId();
  }
}

function historyKey(email, conversationId) {
  return `predictfy_chat_history:${email.toLowerCase()}:${conversationId}`;
}

function initialMessages(user, conversationId) {
  try {
    const saved = localStorage.getItem(historyKey(user.email, conversationId));
    const parsed = saved ? JSON.parse(saved) : null;
    if (Array.isArray(parsed)) {
      const sanitized = parsed
        .filter((message) => message && typeof message === 'object'
          && ['user', 'bot'].includes(message.role) && typeof message.text === 'string')
        .slice(-30)
        .map((message, index) => ({
          ...message,
          id: typeof message.id === 'string' ? message.id : `restored-${index}`,
          streaming: false,
          reasoningOpen: false,
          reasoningComplete: true,
          elapsedMs: Number.isFinite(message.elapsedMs) ? message.elapsedMs : null,
        }));
      if (sanitized.length > 0) return sanitized;
    }
  } catch {
    // Um histórico corrompido não deve impedir a abertura do assistente.
  }
  return [{
    id: 'welcome',
    role: 'bot',
    text: user.welcome || DEFAULT_WELCOME,
    ts: '--:--',
    badge: { label: 'DADOS LOCAIS', tone: 'green' },
    suggestions: DEFAULT_SUGGESTIONS,
  }];
}

function messagesFromArchive(conversation, user) {
  if (!Array.isArray(conversation?.messages) || conversation.messages.length === 0) {
    return initialMessages(user, conversation?.id || 'empty');
  }
  return conversation.messages.map((message, index) => {
    const metadata = message.metadata || {};
    return {
      id: message.id || `archive-${index}`,
      role: message.role === 'assistant' ? 'bot' : 'user',
      text: message.content || '',
      ts: timeFromIso(message.created_at),
      reasoning: metadata.reasoning || '',
      reasoningOpen: false,
      reasoningComplete: true,
      elapsedMs: Number.isFinite(metadata.elapsed_ms) ? metadata.elapsed_ms : null,
      mode: metadata.mode,
      provider: metadata.provider,
      model: metadata.model,
      badge: metadata.badge,
      action: metadata.action,
      suggestions: metadata.suggestions || [],
      analysisMode: metadata.analysis_mode || 'fast',
      sources: metadata.sources || [],
      usage: metadata.usage || {},
      cache: metadata.cache || {},
      responseId: message.response_id || null,
      streaming: false,
    };
  });
}

function sanitizeMarkdown(text) {
  return text
    .replace(/!?\[[^\]]*\]\(\s*(?:https?:\/\/|www\.)[^)]+\)/gi, '[link externo bloqueado]')
    .replace(/(?:https?:\/\/|www\.)\S+/gi, '[link externo bloqueado]');
}

const MARKDOWN_COMPONENTS = {
  a: ({ children }) => <span className="chat-markdown__blocked-link">{children}</span>,
  img: ({ alt }) => <span className="chat-markdown__blocked-link">[{alt || 'imagem bloqueada'}]</span>,
  table: ({ children }) => (
    <div className="chat-markdown__table-wrap" role="region" aria-label="Tabela da resposta" tabIndex="0">
      <table>{children}</table>
    </div>
  ),
};

function MarkdownContent({ text, compact = false }) {
  return (
    <div className={`chat-markdown ${compact ? 'chat-markdown--compact' : ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={MARKDOWN_COMPONENTS}
        skipHtml
      >
        {sanitizeMarkdown(text)}
      </ReactMarkdown>
    </div>
  );
}

function ProviderStatus({ token }) {
  const [status, setStatus] = useState({ state: 'checking', model: 'Assistente', provider: null });
  const [retryTick, setRetryTick] = useState(0);

  useEffect(() => {
    let controller;
    const check = () => {
      controller?.abort();
      controller = new AbortController();
      fetch(`${CHAT_API_BASE}/chat/status`, {
        signal: controller.signal,
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((response) => response.json())
        .then((data) => setStatus({
          state: data.available ? 'online' : 'offline',
          model: data.model || 'Assistente',
          provider: data.provider || null,
        }))
        .catch((requestError) => {
          if (requestError.name !== 'AbortError') setStatus({ state: 'offline', model: 'Assistente', provider: null });
        });
    };
    check();
    const interval = window.setInterval(check, 30_000);
    return () => {
      window.clearInterval(interval);
      controller?.abort();
    };
  }, [retryTick, token]);

  return (
    <button
      type="button"
      className={`chat-provider chat-provider--${status.state}`}
      title={status.state === 'offline' ? 'Análise remota indisponível. Clique para verificar novamente.' : status.model}
      onClick={() => setRetryTick((current) => current + 1)}
      aria-label={status.state === 'offline' ? 'Verificar assistente novamente' : `Assistente ${status.state}`}
    >
      <span aria-hidden="true" />
      {status.state === 'online'
        ? status.provider === 'openai' ? 'LUNA ONLINE' : 'LOCAL ONLINE'
        : status.state === 'offline' ? 'ANÁLISE DEGRADADA' : 'VERIFICANDO'}
    </button>
  );
}

function ReasoningDisclosure({ message, onToggle }) {
  const complete = message.reasoningComplete || Boolean(message.text);
  const label = complete ? 'Análise concluída' : 'Pensando...';

  return (
    <div className={`chat-reasoning ${message.reasoningOpen ? 'chat-reasoning--open' : ''}`}>
      <button
        className="chat-reasoning__toggle"
        onClick={onToggle}
        aria-expanded={Boolean(message.reasoningOpen)}
      >
        <span className={`chat-reasoning__pulse ${complete ? 'chat-reasoning__pulse--done' : ''}`} aria-hidden="true" />
        <span>{label}</span>
        <span className="chat-reasoning__chevron" aria-hidden="true">›</span>
      </button>
      {message.reasoningOpen && (
        <div className="chat-reasoning__content">
          {message.statusLabel && <div className="chat-reasoning__status">{message.statusLabel}</div>}
          {message.reasoning
            ? <MarkdownContent text={message.reasoning} compact />
            : <div className="chat-reasoning__waiting">Aguardando o modelo organizar as evidências…</div>}
        </div>
      )}
    </div>
  );
}

function ChatConversation({
  user,
  conversationId,
  dashboardContext,
  onConversationLoaded,
  onConversationUpdated,
  onSessionExpired,
  onClose,
  active,
}) {
  const navigate = useNavigate();
  const [messages, setMessages] = useState(() => initialMessages(user, conversationId));
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [attachedContext, setAttachedContext] = useState(dashboardContext);
  const [dismissedMismatch, setDismissedMismatch] = useState('');
  const [analysisMode, setAnalysisMode] = useState(() => {
    try {
      return localStorage.getItem(`predictfy_chat_mode:${user.email.toLowerCase()}`) === 'deep'
        ? 'deep'
        : 'fast';
    } catch {
      return 'fast';
    }
  });
  const endRef = useRef(null);
  const messagesRef = useRef(null);
  const inputRef = useRef(null);
  const abortRef = useRef(null);
  const requestInFlightRef = useRef(false);
  const shouldAutoScrollRef = useRef(true);

  useEffect(() => {
    const controller = new AbortController();
    const headers = {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${user.token}`,
    };
    fetch(`${CHAT_API_BASE}/chat/conversations/${conversationId}`, {
      headers,
      signal: controller.signal,
    })
      .then(async (response) => {
        if (response.status === 404) {
          const created = await fetch(`${CHAT_API_BASE}/chat/conversations`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
              conversation_id: conversationId,
              dashboard_context: dashboardContext,
            }),
            signal: controller.signal,
          });
          const body = await created.json().catch(() => ({}));
          if (!created.ok) throw new Error(body.detail || 'Falha ao criar conversa.');
          return body;
        }
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || 'Falha ao carregar conversa.');
        return body;
      })
      .then((conversation) => {
        if (controller.signal.aborted) return;
        if (conversation.message_count > 0) setMessages(messagesFromArchive(conversation, user));
        setAttachedContext(conversation.dashboard_context || dashboardContext);
        onConversationLoaded(conversation);
      })
      .catch((error) => {
        if (error.name !== 'AbortError') onConversationLoaded(null);
      });
    return () => controller.abort();
  }, [conversationId, dashboardContext, onConversationLoaded, user]);

  useEffect(() => {
    try {
      const completed = messages.filter((message) => !message.streaming && message.text).slice(-30);
      if (messages.some((message) => message.streaming) && completed.at(-1)?.role === 'user') completed.pop();
      localStorage.setItem(historyKey(user.email, conversationId), JSON.stringify(completed));
    } catch {
      // Persistência é opcional; o chat continua funcional sem localStorage.
    }
  }, [conversationId, messages, user.email]);

  useEffect(() => {
    try {
      localStorage.setItem(`predictfy_chat_mode:${user.email.toLowerCase()}`, analysisMode);
    } catch {
      // A escolha continua válida durante a sessão atual.
    }
  }, [analysisMode, user.email]);

  const mismatch = contextKey(attachedContext) !== contextKey(dashboardContext);
  const mismatchId = `${contextKey(attachedContext)}>${contextKey(dashboardContext)}`;
  const showContextChoice = mismatch && dismissedMismatch !== mismatchId;

  async function useCurrentDashboardContext() {
    const response = await fetch(`${CHAT_API_BASE}/chat/conversations/${conversationId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${user.token}`,
      },
      body: JSON.stringify({ dashboard_context: dashboardContext }),
    });
    if (!response.ok) return;
    const conversation = await response.json();
    setAttachedContext(conversation.dashboard_context || dashboardContext);
    setDismissedMismatch('');
    onConversationUpdated(conversation);
  }

  useEffect(() => {
    if (shouldAutoScrollRef.current) endRef.current?.scrollIntoView({ behavior: 'auto' });
  }, [messages, thinking]);

  useEffect(() => {
    if (active) inputRef.current?.focus();
  }, [active]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const updateBot = useCallback((id, updater) => {
    setMessages((current) => current.map((message) => (
      message.id === id ? updater(message) : message
    )));
  }, []);

  async function sendMessage(rawText) {
    const text = rawText.trim();
    if (!text || requestInFlightRef.current) return;
    requestInFlightRef.current = true;
    shouldAutoScrollRef.current = true;
    const startedAt = performance.now();

    const userMessage = { id: `user-${Date.now()}`, role: 'user', text, ts: timeNow() };
    const botId = `bot-${Date.now()}`;
    const botMessage = {
      id: botId,
      role: 'bot',
      text: '',
      reasoning: '',
      reasoningOpen: true,
      reasoningComplete: false,
      statusLabel: 'Preparando consulta…',
      elapsedMs: null,
      ts: timeNow(),
      streaming: true,
      analysisMode,
    };
    const history = messages
      .filter((message) => message.text)
      .slice(-8)
      .map((message) => ({
        role: message.role === 'user' ? 'user' : 'assistant',
        content: message.text.slice(0, MAX_MESSAGE_LENGTH),
      }));

    setMessages((current) => [...current, userMessage, botMessage]);
    setInput('');
    setThinking(true);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(`${CHAT_API_BASE}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${user.token}`,
        },
        body: JSON.stringify({
          message: text,
          history,
          conversation_id: conversationId,
          analysis_mode: analysisMode,
          dashboard_context: attachedContext || dashboardContext,
        }),
        signal: controller.signal,
      });

      if (response.status === 401) {
        onSessionExpired();
        return;
      }
      if (!response.ok || !response.body) {
        const failure = await response.json().catch(() => ({}));
        throw new Error(readableErrorDetail(
          failure.detail,
          `Falha HTTP ${response.status}`,
        ));
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finished = false;
      let receivedDone = false;

      while (!finished) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);
          if (event.type === 'meta') {
            updateBot(botId, (message) => ({
              ...message,
              mode: event.mode,
              model: event.model,
              badge: event.badge,
              action: event.action,
              suggestions: event.suggestions,
              responseId: event.response_id,
              analysisMode: event.analysis_mode || message.analysisMode,
            }));
          } else if (event.type === 'status') {
            updateBot(botId, (message) => ({
              ...message,
              statusLabel: event.label,
              reasoningComplete: event.phase === 'answer',
              reasoningOpen: event.phase === 'answer' ? false : message.reasoningOpen,
            }));
          } else if (event.type === 'reasoning') {
            updateBot(botId, (message) => ({
              ...message,
              reasoning: message.reasoning + event.delta,
              reasoningOpen: true,
            }));
          } else if (event.type === 'token') {
            updateBot(botId, (message) => ({
              ...message,
              text: message.text + event.delta,
              reasoningComplete: true,
              reasoningOpen: false,
            }));
          } else if (event.type === 'sources') {
            updateBot(botId, (message) => ({
              ...message,
              sources: Array.isArray(event.items) ? event.items : [],
            }));
          } else if (event.type === 'error') {
            const streamError = new Error(readableErrorDetail(
              event.detail,
              'O provedor analítico falhou.',
            ));
            streamError.elapsedMs = event.elapsed_ms;
            throw streamError;
          } else if (event.type === 'done') {
            receivedDone = true;
            finished = true;
            updateBot(botId, (message) => ({
              ...message,
              streaming: false,
              reasoningComplete: true,
              reasoningOpen: false,
              statusLabel: message.mode === 'deterministic'
                ? 'Consulta direta aos artefatos locais'
                : 'Evidências e limitações utilizadas na resposta',
              elapsedMs: event.elapsed_ms,
              responseId: event.response_id || message.responseId,
              sources: Array.isArray(event.sources) ? event.sources : message.sources,
              usage: event.usage || {},
              cache: event.cache || { hit: false, kind: 'miss' },
            }));
            onConversationUpdated({ id: conversationId });
          }
        }
        if (done) break;
      }
      if (!receivedDone) throw new Error('A conexão foi encerrada antes da confirmação final.');
    } catch (requestError) {
      if (requestError.name === 'AbortError') return;
      updateBot(botId, (message) => ({
        ...message,
        streaming: false,
        reasoningComplete: true,
        reasoningOpen: false,
        statusLabel: 'A análise não pôde ser concluída',
        elapsedMs: requestError.elapsedMs ?? Math.round(performance.now() - startedAt),
        text: message.text || `Não consegui concluir a consulta. ${requestError.message}`,
        badge: { label: 'FALHA NA CONSULTA', tone: 'red' },
        retryText: text,
      }));
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        requestInFlightRef.current = false;
        setThinking(false);
      }
    }
  }

  async function submitFeedback(message, rating) {
    if (!message.responseId || message.feedbackPending) return;
    const previous = message.feedback;
    updateBot(message.id, (current) => ({ ...current, feedback: rating, feedbackPending: true }));
    try {
      const response = await fetch(`${CHAT_API_BASE}/chat/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${user.token}`,
        },
        body: JSON.stringify({ response_id: message.responseId, rating }),
      });
      if (!response.ok) throw new Error('Feedback não aceito');
      updateBot(message.id, (current) => ({ ...current, feedbackPending: false }));
    } catch {
      updateBot(message.id, (current) => ({
        ...current,
        feedback: previous,
        feedbackPending: false,
      }));
    }
  }

  function executeAction(action) {
    if (!ALLOWED_ACTION_ROUTES.has(action?.route)) return;
    navigate(action.route);
    onClose();
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage(input);
  }

  return (
    <>
      {showContextChoice ? (
        <aside className="chat-context-choice" aria-label="Contexto do dashboard alterado">
          <div>
            <span>CONTEXTO ALTERADO</span>
            <strong>
              {attachedContext?.route === dashboardContext.route
                ? `Os filtros de ${dashboardContext.label} mudaram desde a última análise.`
                : `Esta conversa usa ${attachedContext?.label || 'outro dashboard'}; você está em ${dashboardContext.label}.`}
            </strong>
          </div>
          <div className="chat-context-choice__actions">
            <button type="button" onClick={useCurrentDashboardContext}>
              USAR {dashboardContext.label}
            </button>
            <button type="button" onClick={() => setDismissedMismatch(mismatchId)}>
              MANTER {attachedContext?.label || 'ANTERIOR'}
            </button>
          </div>
        </aside>
      ) : null}
      <div
        ref={messagesRef}
        className="chat-messages"
        role="log"
        aria-live="off"
        aria-label="Histórico da conversa"
        onScroll={(event) => {
          const element = event.currentTarget;
          shouldAutoScrollRef.current = element.scrollHeight - element.scrollTop - element.clientHeight < 80;
        }}
      >
        {messages.map((message) => (
          <article key={message.id} className={`chat-message chat-message--${message.role}`}>
            {message.role === 'bot' && (
              <div className="chat-message__avatar" aria-hidden="true">
                <AgentGlyph size={18} active={message.streaming} />
              </div>
            )}
            <div className="chat-message__body">
              {message.role === 'bot' && (message.streaming || message.reasoning) && (
                <ReasoningDisclosure
                  message={message}
                  onToggle={() => updateBot(message.id, (current) => ({
                    ...current,
                    reasoningOpen: !current.reasoningOpen,
                  }))}
                />
              )}
              {(message.text || !message.streaming) && (
                <div className="chat-message__bubble">
                  {message.role === 'bot'
                    ? <MarkdownContent text={message.text} />
                    : <span className="chat-message__plain-text">{message.text}</span>}
                  {message.streaming && <span className="chat-caret" aria-label="Gerando resposta" />}
                </div>
              )}
              {message.badge && (
                <span className={`chat-badge chat-badge--${message.badge.tone || 'purple'}`}>
                  {message.badge.label}
                </span>
              )}
              {message.role === 'bot' && message.sources?.length > 0 && (
                <div className="chat-sources" aria-label="Fontes consultadas">
                  <span>FONTES</span>
                  {message.sources.map((source) => (
                    <span key={source.id || source.label} title={source.kind}>{source.label}</span>
                  ))}
                </div>
              )}
              {message.role === 'bot' && message.cache?.hit && (
                <span className={`chat-cache chat-cache--${message.cache.kind}`}>
                  {message.cache.kind === 'semantic' ? 'CACHE SEMÂNTICO' : 'CACHE VALIDADO'}
                </span>
              )}
              {message.action && (
                <button className="chat-action" onClick={() => executeAction(message.action)}>
                  [ {message.action.label} ] →
                </button>
              )}
              {message.role === 'bot' && message.retryText && !message.streaming ? (
                <button className="chat-retry" type="button" onClick={() => sendMessage(message.retryText)} disabled={thinking}>
                  TENTAR NOVAMENTE
                </button>
              ) : null}
              {message.suggestions?.length > 0 && (
                <div className="chat-suggestions" aria-label="Consultas sugeridas">
                  {message.suggestions.map((suggestion) => (
                    <button key={suggestion} onClick={() => sendMessage(suggestion)} disabled={thinking}>
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
              {message.role === 'bot' && message.elapsedMs != null && (
                <div className="chat-response-meta">
                  <span className="chat-worked">{formatElapsed(message.elapsedMs)}</span>
                  {message.analysisMode === 'deep' && <span>ANÁLISE PROFUNDA</span>}
                  {message.usage?.output_tokens > 0 && (
                    <span title="Tokens de saída medidos pelo provider">
                      {message.usage.output_tokens} TOKENS
                    </span>
                  )}
                  {message.usage?.saved_tokens > 0 && (
                    <span title="Estimativa baseada na geração original reutilizada">
                      {message.usage.saved_tokens} TOKENS ECONOMIZADOS
                    </span>
                  )}
                  {message.responseId && (
                    <span className="chat-feedback" aria-label="Avaliar resposta">
                      <button
                        type="button"
                        className={message.feedback === 'up' ? 'chat-feedback--active' : ''}
                        onClick={() => submitFeedback(message, 'up')}
                        disabled={message.feedbackPending}
                        aria-label="Resposta útil"
                        aria-pressed={message.feedback === 'up'}
                      >
                        <ThumbsUp size={12} strokeWidth={1.7} />
                      </button>
                      <button
                        type="button"
                        className={message.feedback === 'down' ? 'chat-feedback--active' : ''}
                        onClick={() => submitFeedback(message, 'down')}
                        disabled={message.feedbackPending}
                        aria-label="Resposta não útil"
                        aria-pressed={message.feedback === 'down'}
                      >
                        <ThumbsDown size={12} strokeWidth={1.7} />
                      </button>
                    </span>
                  )}
                </div>
              )}
              <time>{message.ts}</time>
            </div>
          </article>
        ))}
        <div ref={endRef} />
      </div>

      <form className="chat-composer" onSubmit={handleSubmit}>
        <div className="chat-mode" role="group" aria-label="Profundidade da análise">
          <button
            type="button"
            className={analysisMode === 'fast' ? 'chat-mode--active' : ''}
            onClick={() => setAnalysisMode('fast')}
            disabled={thinking}
            aria-pressed={analysisMode === 'fast'}
            title="Menor latência e custo; consulta apenas as evidências necessárias"
          >
            <Gauge size={12} /> RÁPIDO
          </button>
          <button
            type="button"
            className={analysisMode === 'deep' ? 'chat-mode--active' : ''}
            onClick={() => setAnalysisMode('deep')}
            disabled={thinking}
            aria-pressed={analysisMode === 'deep'}
            title="Mais raciocínio, ferramentas e orçamento de resposta"
          >
            <BrainCircuit size={12} /> PROFUNDO
          </button>
        </div>
        <div className="chat-composer__field">
          <span aria-hidden="true">&gt;</span>
          <input
            ref={inputRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={thinking ? 'Analisando evidências…' : 'Pergunte sobre riscos, metas ou previsões…'}
            disabled={thinking}
            maxLength={MAX_MESSAGE_LENGTH}
            aria-label="Mensagem para o assistente"
          />
          <button type="submit" disabled={!input.trim() || thinking} aria-label="Enviar mensagem">
            <SendHorizontal size={16} strokeWidth={1.8} />
          </button>
        </div>
        <div className="chat-composer__meta">
          <span>ENTER envia · ESC recolhe</span>
        </div>
      </form>
    </>
  );
}

export default function ChatBot() {
  const { user, logout } = useChatAuth();
  const { width: viewportWidth } = useBreakpoint();
  const { filtroAtivo, filtersByRoute, viewMode } = useDashboard();
  const location = useLocation();
  const [open, setOpen] = useState(() => (
    readPanelOpen(user.email) ?? window.innerWidth >= DOCK_BREAKPOINT
  ));
  const [panelWidth, setPanelWidth] = useState(() => readPanelWidth(user.email));
  const [conversationId, setConversationId] = useState(() => readConversationId(user.email));
  const [activeConversation, setActiveConversation] = useState(null);
  const [panelView, setPanelView] = useState('chat');
  const launcherRef = useRef(null);
  const panelRef = useRef(null);
  const resizeRef = useRef(null);
  const isDocked = viewportWidth >= DOCK_BREAKPOINT;
  const dashboardContext = useMemo(() => {
    const filters = { ...(filtersByRoute[location.pathname] || {}) };
    if (filtroAtivo) filters.filtroAtivo = String(filtroAtivo);
    if (viewMode && viewMode !== 'geral') filters.visualizacaoGlobal = String(viewMode);
    return {
      route: ROUTE_LABELS[location.pathname] ? location.pathname : '/gestao',
      label: ROUTE_LABELS[location.pathname] || 'GESTÃO',
      filters,
    };
  }, [filtroAtivo, filtersByRoute, location.pathname, viewMode]);

  const maximumPanelWidth = useCallback(() => {
    const sidebarWidth = Number.parseFloat(
      getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width'),
    ) || 0;
    return Math.max(
      PANEL_MIN_WIDTH,
      Math.min(PANEL_MAX_WIDTH, window.innerWidth - sidebarWidth - DASHBOARD_MIN_WIDTH),
    );
  }, []);

  const effectiveWidth = Math.min(panelWidth, maximumPanelWidth());

  const persistOpen = useCallback((nextOpen) => {
    setOpen(nextOpen);
    try {
      localStorage.setItem(panelPreferenceKey(user.email, 'open'), String(nextOpen));
    } catch {
      // Preferências visuais não devem bloquear o uso do agente.
    }
  }, [user.email]);

  const close = useCallback(() => {
    persistOpen(false);
    window.requestAnimationFrame(() => launcherRef.current?.focus());
  }, [persistOpen]);

  const openPanel = useCallback(() => {
    persistOpen(true);
  }, [persistOpen]);

  const commitPanelWidth = useCallback((nextWidth) => {
    const bounded = clamp(nextWidth, PANEL_MIN_WIDTH, maximumPanelWidth());
    setPanelWidth(bounded);
    panelRef.current?.style.setProperty('--chat-panel-width', `${bounded}px`);
    try {
      localStorage.setItem(panelPreferenceKey(user.email, 'width'), String(Math.round(bounded)));
    } catch {
      // O redimensionamento continua funcionando sem persistência.
    }
  }, [maximumPanelWidth, user.email]);

  function handleResizeStart(event) {
    if (!isDocked) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    resizeRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startWidth: effectiveWidth,
      width: effectiveWidth,
    };
    document.body.classList.add('chat-is-resizing');
  }

  function handleResizeMove(event) {
    const resize = resizeRef.current;
    if (!resize || resize.pointerId !== event.pointerId) return;
    const nextWidth = clamp(
      resize.startWidth + resize.startX - event.clientX,
      PANEL_MIN_WIDTH,
      maximumPanelWidth(),
    );
    resize.width = nextWidth;
    panelRef.current?.style.setProperty('--chat-panel-width', `${nextWidth}px`);
  }

  function handleResizeEnd(event) {
    const resize = resizeRef.current;
    if (!resize || resize.pointerId !== event.pointerId) return;
    resizeRef.current = null;
    document.body.classList.remove('chat-is-resizing');
    commitPanelWidth(resize.width);
  }

  function handleResizeKey(event) {
    if (!['ArrowLeft', 'ArrowRight', 'Home'].includes(event.key)) return;
    event.preventDefault();
    if (event.key === 'Home') {
      commitPanelWidth(PANEL_DEFAULT_WIDTH);
      return;
    }
    commitPanelWidth(effectiveWidth + (event.key === 'ArrowLeft' ? 24 : -24));
  }

  const handleConversationLoaded = useCallback((conversation) => {
    if (conversation) setActiveConversation(conversation);
  }, []);

  const refreshConversation = useCallback((conversation) => {
    if (conversation?.dashboard_context || conversation?.title) {
      setActiveConversation(conversation);
      return;
    }
    fetch(`${CHAT_API_BASE}/chat/conversations/${conversationId}`, {
      headers: { Authorization: `Bearer ${user.token}` },
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => { if (body) setActiveConversation(body); })
      .catch(() => {});
  }, [conversationId, user.token]);

  function persistConversationId(nextId) {
    setConversationId(nextId);
    try {
      localStorage.setItem(conversationPreferenceKey(user.email), nextId);
    } catch {
      // A conversa continua ativa durante a sessão.
    }
  }

  function startNewConversation() {
    const nextId = createConversationId();
    persistConversationId(nextId);
    setPanelView('chat');
    setActiveConversation({
      id: nextId,
      title: 'Nova análise operacional',
      dashboard_context: dashboardContext,
      message_count: 0,
    });
    fetch(`${CHAT_API_BASE}/chat/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${user.token}`,
      },
      body: JSON.stringify({
        conversation_id: nextId,
        dashboard_context: dashboardContext,
      }),
    }).catch(() => {});
  }

  function selectConversation(conversation) {
    persistConversationId(conversation.id);
    setActiveConversation(conversation);
    setPanelView('chat');
  }

  useEffect(() => {
    function handleKeys(event) {
      if (event.key === 'Escape' && open) {
        if (panelView === 'history') setPanelView('chat');
        else close();
        return;
      }
      if (isDocked || event.key !== 'Tab' || !panelRef.current) return;
      const focusable = [...panelRef.current.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      )];
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    if (open) {
      window.addEventListener('keydown', handleKeys);
      if (!isDocked) document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeys);
      document.body.style.overflow = '';
      document.body.classList.remove('chat-is-resizing');
    };
  }, [close, isDocked, open, panelView]);

  return (
    <>
      <button
        ref={launcherRef}
        className={`chat-launcher ${open ? 'chat-launcher--hidden' : ''}`}
        onClick={openPanel}
        aria-label="Abrir assistente Predictfy"
        aria-expanded={open}
      >
        <span className="chat-launcher__icon"><AgentGlyph size={30} active /></span>
        <span className="chat-launcher__label">PREDICTFY<br />AGENT</span>
        <span className="chat-launcher__status" aria-hidden="true" />
      </button>

      {open && !isDocked && (
        <button className="chat-backdrop" onClick={close} aria-label="Fechar assistente" />
      )}

      <section
        ref={panelRef}
        className={`chat-console ${open ? 'chat-console--open' : 'chat-console--closed'}`}
        style={{ '--chat-panel-width': `${effectiveWidth}px` }}
        role={isDocked ? 'complementary' : 'dialog'}
        aria-modal={isDocked ? undefined : true}
        aria-hidden={!open}
        inert={!open}
        aria-label="Predictfy Agent"
      >
        <div
          className="chat-resizer"
          role="separator"
          aria-label="Redimensionar painel do agente"
          aria-orientation="vertical"
          aria-valuemin={PANEL_MIN_WIDTH}
          aria-valuemax={Math.round(maximumPanelWidth())}
          aria-valuenow={Math.round(effectiveWidth)}
          tabIndex="0"
          title="Arraste para redimensionar · Duplo clique para restaurar"
          onPointerDown={handleResizeStart}
          onPointerMove={handleResizeMove}
          onPointerUp={handleResizeEnd}
          onPointerCancel={handleResizeEnd}
          onDoubleClick={() => commitPanelWidth(PANEL_DEFAULT_WIDTH)}
          onKeyDown={handleResizeKey}
        >
          <span aria-hidden="true" />
        </div>

        <header className="chat-header">
          <div className="chat-header__identity">
            <div className="chat-header__mark"><AgentGlyph size={24} active /></div>
            <div>
              <strong>{panelView === 'history' ? 'CONVERSATION ' : 'PREDICTFY '}<em>{panelView === 'history' ? 'ARCHIVE' : 'AGENT'}</em></strong>
              <small>{panelView === 'history' ? 'SEARCH / ORGANIZE / RESUME' : 'OPERATIONAL INTELLIGENCE'}</small>
            </div>
          </div>
          <div className="chat-header__tools">
            <ProviderStatus token={user.token} />
            <button
              onClick={() => setPanelView((current) => (current === 'history' ? 'chat' : 'history'))}
              aria-label={panelView === 'history' ? 'Voltar para conversa' : 'Abrir histórico'}
              title={panelView === 'history' ? 'Voltar para conversa' : 'Histórico'}
            >
              <History size={16} strokeWidth={1.6} />
            </button>
            <button onClick={startNewConversation} aria-label="Iniciar nova conversa" title="Nova conversa">
              <Plus size={16} strokeWidth={1.6} />
            </button>
            <button onClick={close} aria-label="Recolher assistente" title="Recolher painel">
              <PanelRightClose size={17} strokeWidth={1.6} />
            </button>
          </div>
        </header>

        {panelView === 'chat' ? (
          <>
            <div className="chat-context-strip">
              <span className="chat-context-strip__live"><i aria-hidden="true" /> CONTEXTO ATIVO</span>
              <span>{dashboardContext.label}</span>
              <span title={activeConversation?.title || 'Nova análise operacional'}>
                {activeConversation?.title || 'NOVA ANÁLISE'}
              </span>
            </div>

            <ChatConversation
              key={`${user.email}:${conversationId}`}
              user={user}
              conversationId={conversationId}
              dashboardContext={dashboardContext}
              onConversationLoaded={handleConversationLoaded}
              onConversationUpdated={refreshConversation}
              onSessionExpired={logout}
              onClose={() => { if (!isDocked) close(); }}
              active={open}
            />
          </>
        ) : (
          <ChatHistory
            token={user.token}
            activeConversationId={conversationId}
            onBack={() => setPanelView('chat')}
            onNew={startNewConversation}
            onSelect={selectConversation}
          />
        )}
      </section>
    </>
  );
}
