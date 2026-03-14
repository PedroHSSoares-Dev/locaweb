import { servers, horizonForProb } from '../data/mockData';
import { AlertTriangle, Zap, Network, HardDrive, ChevronRight } from 'lucide-react';

const ISSUE_META = {
  queda_servidor: { label: 'Queda de Servidor', icon: Zap, color: 'var(--red)' },
  falha_rede: { label: 'Falha de Rede', icon: Network, color: 'var(--orange)' },
  esgotamento_recursos: { label: 'Esgotamento de Recursos', icon: HardDrive, color: 'var(--yellow)' },
};

function SeverityIcon({ failProb }) {
  const color = failProb >= 80 ? 'var(--red)' : failProb >= 60 ? 'var(--orange)' : failProb >= 40 ? 'var(--yellow)' : 'var(--green)';
  const size = failProb >= 80 ? 14 : 12;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      width: 28, height: 28, borderRadius: '50%',
      background: `${color}18`,
      flexShrink: 0,
      animation: failProb >= 80 ? 'pulse-glow 2s ease-in-out infinite' : 'none',
    }}>
      <AlertTriangle size={size} color={color} strokeWidth={2.5} />
    </div>
  );
}

function ProbBadge({ prob }) {
  const color = prob >= 80 ? 'var(--red)' : prob >= 60 ? 'var(--orange)' : prob >= 40 ? 'var(--yellow)' : 'var(--green)';
  return (
    <div style={{
      fontFamily: 'var(--font-mono)', fontWeight: 700,
      fontSize: 13, color,
      minWidth: 44, textAlign: 'right',
    }}>
      {prob}%
    </div>
  );
}

function MiniStat({ label, value, color }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1,
    }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: color || 'var(--text-sec)' }}>
        {value}
      </span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.06em' }}>
        {label}
      </span>
    </div>
  );
}

function AlertRow({ server, horizon, viewMode, onSelect, index }) {
  const meta = ISSUE_META[server.predictedIssue] || ISSUE_META.queda_servidor;
  const IssueIcon = meta.icon;
  const isCritical = server.failProb >= 80;

  return (
    <div
      onClick={() => onSelect(server)}
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        cursor: 'pointer',
        transition: 'background 0.15s ease',
        animation: `fadeInUp 0.3s ease ${index * 40}ms both`,
        borderLeft: isCritical ? '2px solid var(--red)' : '2px solid transparent',
        position: 'relative',
      }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--surface2)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      <SeverityIcon failProb={server.failProb} />

      {/* Name + product */}
      <div style={{ flex: '0 0 160px' }}>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 600,
          color: 'var(--text-pri)',
        }}>
          {server.name}
        </div>
        <div style={{
          fontFamily: 'var(--font-sans)', fontSize: 10,
          color: 'var(--text-muted)', marginTop: 1,
        }}>
          {server.product}
        </div>
      </div>

      {/* Issue type */}
      <div style={{ flex: '0 0 180px', display: 'flex', alignItems: 'center', gap: 6 }}>
        <IssueIcon size={11} color={meta.color} strokeWidth={2.5} />
        <span style={{
          fontFamily: 'var(--font-sans)', fontSize: 11,
          color: 'var(--text-sec)',
        }}>
          {meta.label}
        </span>
      </div>

      {/* Prob */}
      <div style={{ flex: '0 0 60px' }}>
        <ProbBadge prob={server.failProb} />
      </div>

      {/* Horizon */}
      <div style={{ flex: '0 0 70px' }}>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: 11,
          color: 'var(--text-sec)',
        }}>
          {horizonForProb(server.failProb, horizon)}
        </span>
      </div>

      {/* Technical columns */}
      {viewMode === 'tecnica' && (
        <>
          <MiniStat label="CPU" value={`${server.cpu}%`} color={server.cpu > 80 ? 'var(--red)' : 'var(--text-sec)'} />
          <div style={{ width: 1 }} />
          <MiniStat label="RAM" value={`${server.ram}%`} color={server.ram > 85 ? 'var(--orange)' : 'var(--text-sec)'} />
          <div style={{ width: 1 }} />
          <MiniStat label="Latência" value={`${server.latency}ms`} color={server.latency > 200 ? 'var(--yellow)' : 'var(--text-sec)'} />
        </>
      )}

      <div style={{ marginLeft: 'auto' }}>
        <button
          onClick={e => { e.stopPropagation(); onSelect(server); }}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 10px', borderRadius: 4,
            fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 600,
            color: server.failProb >= 80 ? 'var(--red)' : 'var(--text-sec)',
            border: `1px solid ${server.failProb >= 80 ? 'rgba(232,0,45,0.3)' : 'var(--border)'}`,
            background: server.failProb >= 80 ? 'var(--red-dim)' : 'transparent',
            transition: 'all 0.15s',
            letterSpacing: '0.06em',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = 'var(--red)';
            e.currentTarget.style.color = 'var(--red)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = server.failProb >= 80 ? 'rgba(232,0,45,0.3)' : 'var(--border)';
            e.currentTarget.style.color = server.failProb >= 80 ? 'var(--red)' : 'var(--text-sec)';
          }}
        >
          Investigar <ChevronRight size={10} />
        </button>
      </div>
    </div>
  );
}

export default function AlertsList({ horizon, viewMode, onSelectServer }) {
  const sorted = [...servers].sort((a, b) => b.failProb - a.failProb);
  const displayed = viewMode === 'geral' ? sorted.slice(0, 5) : sorted;

  const colHeaders = viewMode === 'tecnica'
    ? ['SERVIDOR', 'TIPO DE FALHA', 'PROB.', 'HORIZONTE', 'CPU', '', 'RAM', '', 'LATÊNCIA', '']
    : ['SERVIDOR', 'TIPO DE FALHA', 'PROB.', 'HORIZONTE', ''];

  return (
    <div style={{
      background: 'var(--surface1)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 16px 10px',
        borderBottom: '1px solid var(--border)',
      }}>
        <div>
          <div style={{
            fontFamily: 'var(--font-sans)', fontWeight: 600,
            fontSize: 13, color: 'var(--text-pri)',
          }}>
            Alertas de Predição
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--text-muted)', marginTop: 2,
          }}>
            {viewMode === 'geral' ? `Top 5 de ${servers.length} servidores` : `Todos os ${servers.length} servidores`} · ordenado por risco
          </div>
        </div>
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 10,
          color: 'var(--red)', letterSpacing: '0.08em',
          background: 'var(--red-dim)', padding: '3px 8px',
          borderRadius: 4, border: '1px solid rgba(232,0,45,0.2)',
        }}>
          {servers.filter(s => s.failProb >= 80).length} CRÍTICOS
        </div>
      </div>

      {/* Column headers */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '6px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface2)',
      }}>
        <div style={{ width: 28 }} />
        <div style={{
          flex: '0 0 160px',
          fontFamily: 'var(--font-mono)', fontSize: 9,
          color: 'var(--text-muted)', letterSpacing: '0.12em',
        }}>SERVIDOR</div>
        <div style={{
          flex: '0 0 180px',
          fontFamily: 'var(--font-mono)', fontSize: 9,
          color: 'var(--text-muted)', letterSpacing: '0.12em',
        }}>TIPO DE FALHA</div>
        <div style={{
          flex: '0 0 60px',
          fontFamily: 'var(--font-mono)', fontSize: 9,
          color: 'var(--text-muted)', letterSpacing: '0.12em',
          textAlign: 'right',
        }}>PROB.</div>
        <div style={{
          flex: '0 0 70px',
          fontFamily: 'var(--font-mono)', fontSize: 9,
          color: 'var(--text-muted)', letterSpacing: '0.12em',
        }}>HORIZONTE</div>
        {viewMode === 'tecnica' && (
          <>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.12em' }}>CPU</div>
            <div style={{ width: 1 }} />
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.12em' }}>RAM</div>
            <div style={{ width: 1 }} />
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.12em' }}>LATÊNCIA</div>
          </>
        )}
        <div style={{ marginLeft: 'auto' }} />
      </div>

      {/* Rows */}
      <div>
        {displayed.map((server, i) => (
          <AlertRow
            key={server.id}
            server={server}
            horizon={horizon}
            viewMode={viewMode}
            onSelect={onSelectServer}
            index={i}
          />
        ))}
      </div>
    </div>
  );
}
