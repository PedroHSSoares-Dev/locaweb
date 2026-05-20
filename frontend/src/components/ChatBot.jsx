import { useState, useRef, useEffect } from 'react';
import LogoPredictfy from './LogoPredictfy';

// ── Respostas mockadas ────────────────────────────────────────────────────────
const MOCK_RESPONSES = {
  cluster: {
    text: 'C3 é o cluster mais crítico — Operação Fora do Horário. Taxa de violação: **2.1%** vs média 0.97%. 2.813 incidentes · Team05 · Sáb/Dom/Sex.',
    badge: { label: 'C3 CRÍTICO', color: 'var(--red)', bg: 'var(--red-dim)' },
    action: { label: 'VER CENTRO TÉCNICO', route: '/tecnico' },
    suggestions: ['Por que C3 viola mais?', 'Comparar C1 vs C3', 'Time responsável'],
  },
  violacao: {
    text: 'Em 2025: P2 registrou **42 violações** (67.7% da cota anual). P3 registrou **206 violações** (73.3% da cota). Ambos dentro da meta SPC.',
    badge: { label: 'DENTRO DA META', color: 'var(--green)', bg: 'var(--green-dim)' },
    action: { label: 'VER GESTÃO', route: '/gestao' },
    suggestions: ['Quais meses foram anomalias?', 'Meta do próximo período'],
  },
  previsao: {
    text: 'Previsão LSTM para amanhã (D+1): **69 incidentes** · P2: 13 · P3: 57. Horizonte D+7: **65 incidentes** (média semanal).',
    badge: { label: 'D+1: 69 INC', color: 'var(--teal)', bg: 'var(--teal-dim)' },
    action: { label: 'VER MONITORAMENTO', route: '/monitoramento' },
    suggestions: ['Como o LSTM funciona?', 'Comparar com semana passada'],
  },
  risco: {
    text: 'Risco de violação OLA por prioridade — P3: **28.2%** de probabilidade média (ATENÇÃO). P2: **3.9%** (NOMINAL). Modelo XGBoost · ROC-AUC 0.84.',
    badge: { label: 'P3 ATENÇÃO 28.2%', color: 'var(--orange)', bg: 'var(--orange-dim)' },
    action: { label: 'VER ANÁLISE PREDITIVA', route: '/monitoramento' },
    suggestions: ['Por que P3 viola mais?', 'Top fatores de risco'],
  },
  shap: {
    text: 'Top 3 fatores de risco (SHAP values): 1. **Prioridade P2/P3** (67.6%) · 2. Frequência histórica do grupo (53.4%) · 3. Subcategoria do incidente (47.3%).',
    badge: { label: 'SHAP · TOP FEATURE: PRIORIDADE', color: 'var(--purple)', bg: 'rgba(191,90,242,0.12)' },
    action: { label: 'VER FATORES DE RISCO', route: '/tecnico' },
    suggestions: ['Como o XGBoost foi treinado?', 'Ver todos os fatores'],
  },
  default: {
    text: 'Não reconheci a consulta. Tente perguntar sobre clusters, violações, previsões ou fatores de risco.',
    badge: null,
    action: null,
    suggestions: ['Cluster mais crítico', 'Previsão amanhã', 'Fatores de risco hoje'],
  },
};

function getResponse(input) {
  const q = input.toLowerCase();
  if (q.match(/cluster|c3|c0|c1|c2|segmenta/)) return MOCK_RESPONSES.cluster;
  if (q.match(/violaç|viola|ola|meta|cota/)) return MOCK_RESPONSES.violacao;
  if (q.match(/previs|amanhã|d\+1|d\+7|lstm|volume/)) return MOCK_RESPONSES.previsao;
  if (q.match(/risco|xgboost|probabilidade|p2|p3/)) return MOCK_RESPONSES.risco;
  if (q.match(/shap|fator|feature|importância/)) return MOCK_RESPONSES.shap;
  return MOCK_RESPONSES.default;
}

function ChatButtonLogo({ size = 28, color = 'currentColor' }) {
  return (
    <svg
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="31 31 258 258"
      width={size}
      height={size}
      style={{ display: 'block', color }}
    >
      <rect x="40" y="40" width="240" height="240" rx="45" stroke="currentColor" strokeWidth="18" fill="none" strokeLinejoin="round" />
      <path d="M 60 260 L 120 140 L 170 190 L 230 100" stroke="currentColor" strokeWidth="18" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="120" cy="140" r="20" stroke="currentColor" strokeWidth="18" fill="none" />
      <circle cx="170" cy="190" r="20" stroke="currentColor" strokeWidth="18" fill="none" />
      <circle cx="230" cy="100" r="20" stroke="currentColor" strokeWidth="18" fill="none" />
    </svg>
  );
}

// ── Componente principal ──────────────────────────────────────────────────────
export default function ChatBot() {
  // 'closed' | 'loading' | 'open'
  const [phase, setPhase] = useState('closed');
  const isClosed  = phase === 'closed';
  const isLoading = phase === 'loading';
  const isOpen    = phase === 'open';
  const timerRef  = useRef(null);
  const [motionReady, setMotionReady] = useState(false);

  function openChat() {
    if (timerRef.current) clearTimeout(timerRef.current);
    setPhase('loading');
  }

  function closeChat() {
    if (timerRef.current) clearTimeout(timerRef.current);
    setPhase('closed');
  }

  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);

  useEffect(() => {
    if (!isLoading) return undefined;
    timerRef.current = setTimeout(() => setPhase('open'), 360);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [isLoading]);

  useEffect(() => {
    let frame2 = null;
    const frame1 = requestAnimationFrame(() => {
      frame2 = requestAnimationFrame(() => setMotionReady(true));
    });
    return () => {
      cancelAnimationFrame(frame1);
      if (frame2) cancelAnimationFrame(frame2);
    };
  }, []);

  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'bot',
      text: 'SYSTEM READY. Monitorando 4 clusters · 25.006 incidentes KPI. Contexto 2023–2025 carregado. Como posso ajudar?',
      badge: null,
      action: null,
      suggestions: ['Cluster mais crítico', 'Previsão amanhã', 'Fatores de risco hoje'],
      ts: '16:14',
    },
    {
      id: 2,
      role: 'user',
      text: 'qual cluster está mais crítico agora?',
      ts: '16:15',
    },
    {
      id: 3,
      role: 'bot',
      text: 'C3 é o cluster mais crítico — Operação Fora do Horário. Taxa de violação: **2.1%** vs média 0.97%. 2.813 incidentes · Team05 · Sáb/Dom/Sex.',
      badge: { label: 'C3 CRÍTICO', color: 'var(--red)', bg: 'var(--red-dim)' },
      action: { label: 'VER CENTRO TÉCNICO', route: '/tecnico' },
      suggestions: ['Por que C3 viola mais?', 'Comparar C1 vs C3', 'Time responsável'],
      ts: '16:15',
    },
  ]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return;
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinking, isOpen]);

  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 50);
  }, [isOpen]);

  useEffect(() => {
    function onKeyDown(e) { if (e.key === 'Escape' && isOpen) closeChat(); }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen]);

  function sendMessage(text) {
    if (!text.trim() || thinking) return;
    const userMsg = {
      id: Date.now(),
      role: 'user',
      text: text.trim(),
      ts: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setThinking(true);

    setTimeout(() => {
      const resp = getResponse(text);
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'bot',
        text: resp.text,
        badge: resp.badge,
        action: resp.action,
        suggestions: resp.suggestions,
        ts: new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
      }]);
      setThinking(false);
    }, 900 + Math.random() * 600);
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  }

  function parseText(text) {
    const parts = text.split(/\*\*(.*?)\*\*/g);
    return parts.map((p, i) =>
      i % 2 === 1
        ? <strong key={i} style={{ color: 'var(--text-pri)', fontWeight: 600 }}>{p}</strong>
        : p
    );
  }

  const buttonSize = 48;
  const buttonBottom = 24;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={() => isOpen && closeChat()}
        style={{
          position: 'fixed', inset: 0, zIndex: 998,
          background: 'rgba(0,0,0,0.72)',
          opacity: isOpen ? 1 : 0,
          transition: 'opacity 0.22s ease',
          pointerEvents: isOpen ? 'all' : 'none',
        }}
      />

      {/* ── Elemento único — botão E modal ───────────────────────────────── */}
      <div
        onClick={isClosed ? openChat : undefined}
        style={{
          position: 'fixed',
          zIndex: 999,
          cursor: isClosed ? 'pointer' : 'default',
          overflow: 'hidden',

          top: isClosed ? `calc(100dvh - ${buttonSize + buttonBottom}px)` : '50%',
          left: '50%',
          transform: isClosed
            ? 'translate3d(-50%, 0, 0)'
            : 'translate3d(-50%, -50%, 0)',

          width:  isClosed ? 48  : 680,
          height: isClosed ? 48  : 620,
          maxWidth:  'calc(100vw - 32px)',
          maxHeight: 'calc(100vh - 60px)',

          borderRadius: isClosed ? 24 : 12,

          background: isOpen ? 'var(--surface1)' : 'var(--purple)',
          border: isOpen
            ? '1px solid var(--border)'
            : '1.5px solid var(--purple)',

          display: 'flex',
          flexDirection: 'column',
          alignItems: isOpen ? 'stretch' : 'center',
          justifyContent: isOpen ? 'flex-start' : 'center',

          willChange: 'width, height, transform, border-radius, background',
          transition: motionReady ? [
            'top 0.32s cubic-bezier(0.16, 1, 0.3, 1)',
            'width 0.32s cubic-bezier(0.16, 1, 0.3, 1)',
            'height 0.32s cubic-bezier(0.16, 1, 0.3, 1)',
            'transform 0.32s cubic-bezier(0.16, 1, 0.3, 1)',
            'border-radius 0.32s ease',
            'background 0.2s ease',
            'border-color 0.2s ease',
          ].join(', ') : 'none',
        }}
      >
        {/* ── Camada roxa — closed + loading ─────────────────────────────── */}
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'var(--purple)',
          opacity: isOpen ? 0 : 1,
          transition: motionReady ? 'opacity 0.22s ease' : 'none',
          pointerEvents: 'none',
          zIndex: 2,
          overflow: 'hidden',
        }}>
          <div style={{
            position: 'relative',
            width:  isLoading ? 160 : 28,
            height: isLoading ? 160 : 28,
            transition: motionReady && !isClosed ? 'width 0.3s ease, height 0.3s ease' : 'none',
            overflow: 'hidden',
          }}>
            {isClosed ? (
              <ChatButtonLogo size={28} color="rgba(255,255,255,0.92)" />
            ) : (
              <LogoPredictfy
                size={160}
                color="rgba(255,255,255,0.92)"
                style={{ display: 'block', transition: motionReady ? 'all 0.3s ease' : 'none' }}
              />
            )}
            {isLoading && (
              <div style={{
                position: 'absolute',
                top: 0, left: 0, width: '100%', height: '100%',
                background: 'linear-gradient(105deg, transparent 25%, rgba(255,255,255,0.5) 50%, transparent 75%)',
                animation: 'shimmer-logo 1.3s ease-in-out infinite',
                pointerEvents: 'none',
              }} />
            )}
          </div>
        </div>

        {/* ── Conteúdo do chat (fase open) ───────────────────────────────── */}
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', flexDirection: 'column',
          opacity: isOpen ? 1 : 0,
          transition: isOpen ? 'opacity 0.22s ease 0.08s' : 'opacity 0.1s ease',
          pointerEvents: isOpen ? 'all' : 'none',
          zIndex: 1,
        }}>
          {/* Header */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '12px 18px',
            background: 'var(--surface2)',
            borderBottom: '1px solid var(--border)',
            flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                width: 26, height: 26,
                border: '1.5px solid var(--purple)',
                borderRadius: 5,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <LogoPredictfy size={14} color="var(--purple)" />
              </div>
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 13,
                color: 'var(--purple)', letterSpacing: '0.12em', fontWeight: 600,
              }}>PREDICTFY_ASSISTANT</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <div style={{
                  width: 7, height: 7, borderRadius: '50%',
                  background: 'var(--green)',
                  boxShadow: '0 0 0 2px var(--green-dim)',
                  animation: 'pulse-dot 2s ease infinite',
                }} />
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--green)', letterSpacing: '0.08em' }}>ONLINE</span>
              </div>
              <button
                onClick={closeChat}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 18, padding: '2px 4px', lineHeight: 1 }}
              >✕</button>
            </div>
          </div>

          {/* Messages area */}
          <div style={{
            flex: 1, overflowY: 'auto', overflowX: 'hidden',
            padding: '18px 18px',
            display: 'flex', flexDirection: 'column', gap: 14,
          }}>
            {messages.map((msg) => (
              <div key={msg.id} style={{
                display: 'flex',
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                alignItems: 'flex-start',
                gap: 10,
              }}>
                {msg.role === 'bot' && (
                  <div style={{
                    width: 32, height: 32, borderRadius: '50%',
                    background: 'var(--surface3)',
                    border: '1px solid var(--border)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0, marginTop: 2,
                  }}>
                    <LogoPredictfy size={16} color="var(--purple)" />
                  </div>
                )}

                <div style={{
                  display: 'flex', flexDirection: 'column',
                  alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  maxWidth: '75%',
                  gap: 5,
                }}>
                  <div style={{
                    padding: msg.role === 'user' ? '10px 14px' : '11px 15px',
                    background: msg.role === 'user' ? 'var(--surface4)' : 'transparent',
                    border: msg.role === 'user' ? '1px solid var(--border)' : 'none',
                    borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 13,
                    color: msg.role === 'user' ? 'var(--text-pri)' : 'var(--text-sec)',
                    lineHeight: 1.65,
                  }}>
                    {msg.role === 'user' ? msg.text : parseText(msg.text)}
                  </div>

                  {msg.role === 'bot' && msg.badge && (
                    <span style={{
                      fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
                      color: msg.badge.color,
                      background: msg.badge.bg,
                      border: `1px solid ${msg.badge.color}55`,
                      borderRadius: 3, padding: '3px 9px',
                      alignSelf: 'flex-start',
                    }}>{msg.badge.label}</span>
                  )}

                  {msg.role === 'bot' && msg.action && (
                    <a
                      href={msg.action.route}
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: 6,
                        fontFamily: 'var(--font-mono)', fontSize: 11,
                        color: 'var(--text-muted)', letterSpacing: '0.06em',
                        background: 'var(--surface2)',
                        border: '1px solid var(--border)',
                        borderRadius: 4, padding: '5px 11px',
                        textDecoration: 'none',
                        alignSelf: 'flex-start',
                        transition: 'border-color 0.15s, color 0.15s',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--purple)'; e.currentTarget.style.color = 'var(--purple)'; }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-muted)'; }}
                    >
                      [ EXECUTE: {msg.action.label} ] →
                    </a>
                  )}

                  {msg.role === 'bot' && msg.suggestions && (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignSelf: 'flex-start' }}>
                      {msg.suggestions.map(s => (
                        <button
                          key={s}
                          onClick={() => sendMessage(s)}
                          style={{
                            fontFamily: 'var(--font-mono)', fontSize: 11,
                            color: 'var(--purple)',
                            background: 'transparent',
                            border: '1px solid rgba(191,90,242,0.3)',
                            borderRadius: 4, padding: '4px 9px',
                            cursor: 'pointer',
                            transition: 'background 0.15s, border-color 0.15s',
                          }}
                          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(191,90,242,0.12)'; e.currentTarget.style.borderColor = 'var(--purple)'; }}
                          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'rgba(191,90,242,0.3)'; }}
                        >{s}</button>
                      ))}
                    </div>
                  )}

                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 10,
                    color: 'var(--text-muted)', letterSpacing: '0.06em',
                  }}>{msg.ts}</span>
                </div>
              </div>
            ))}

            {thinking && (
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%',
                  background: 'var(--surface3)', border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0, marginTop: 2,
                }}>
                  <LogoPredictfy size={16} color="var(--purple)" />
                </div>
                <div style={{ padding: '12px 0', display: 'flex', alignItems: 'center', gap: 10 }}>
                  <div style={{ width: 110, height: 3, background: 'var(--surface4)', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: '40%', background: 'var(--purple)', borderRadius: 2, animation: 'scan 1.4s linear infinite' }} />
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>processando...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div style={{
            padding: '12px 16px',
            background: 'var(--surface2)',
            borderTop: '1px solid var(--border)',
            flexShrink: 0,
          }}>
            <div
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                background: 'var(--surface3)',
                border: '1px solid var(--border)',
                borderRadius: 6, padding: '10px 12px',
                transition: 'border-color 0.15s',
              }}
              onFocusCapture={e => e.currentTarget.style.borderColor = 'var(--purple)'}
              onBlurCapture={e => e.currentTarget.style.borderColor = 'var(--border)'}
            >
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--purple)', flexShrink: 0 }}>&gt;&nbsp;</span>
              <input
                ref={inputRef}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="consulta operacional..."
                disabled={thinking}
                style={{
                  flex: 1, background: 'none', border: 'none', outline: 'none',
                  fontFamily: 'var(--font-mono)', fontSize: 13,
                  color: 'var(--text-pri)',
                  caretColor: 'var(--purple)',
                }}
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || thinking}
                style={{
                  background: 'none', border: 'none', cursor: input.trim() ? 'pointer' : 'default',
                  fontFamily: 'var(--font-mono)', fontSize: 13,
                  color: input.trim() ? 'var(--purple)' : 'var(--text-muted)',
                  padding: '0 2px', transition: 'color 0.15s',
                }}
              >↵</button>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text-muted)', marginTop: 6, letterSpacing: '0.06em', textAlign: 'center' }}>
              ENTER para enviar · ESC para fechar
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes shimmer-logo {
          0%   { transform: translateX(-150%); }
          100% { transform: translateX(250%);  }
        }
        @keyframes scan {
          0%   { transform: translateX(-200%); }
          100% { transform: translateX(400%);  }
        }
        @keyframes pulse-dot {
          0%, 100% { opacity: 1 }
          50%       { opacity: 0.4 }
        }
      `}</style>
    </>
  );
}
