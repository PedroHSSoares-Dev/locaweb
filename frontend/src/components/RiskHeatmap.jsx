import { getServersByProduct } from '../data/mockData';

function riskColor(failProb) {
  if (failProb >= 80) return { bg: 'rgba(232,0,45,0.18)', border: 'rgba(232,0,45,0.5)', text: '#E8002D' };
  if (failProb >= 60) return { bg: 'rgba(255,109,0,0.15)', border: 'rgba(255,109,0,0.45)', text: '#ff6d00' };
  if (failProb >= 40) return { bg: 'rgba(255,234,0,0.12)', border: 'rgba(255,234,0,0.35)', text: '#ffea00' };
  return { bg: 'rgba(0,230,118,0.07)', border: 'rgba(0,230,118,0.2)', text: '#00e676' };
}

function riskLabel(failProb) {
  if (failProb >= 80) return 'CRÍTICO';
  if (failProb >= 60) return 'ALTO';
  if (failProb >= 40) return 'MÉDIO';
  return 'BAIXO';
}

function ServerCell({ server, onClick }) {
  const colors = riskColor(server.failProb);
  const isCritical = server.failProb >= 80;
  const delta = server.probDelta;

  return (
    <div
      onClick={() => onClick(server)}
      style={{
        background: colors.bg,
        border: `1px solid ${colors.border}`,
        borderRadius: 6,
        padding: '10px 12px',
        cursor: 'pointer',
        transition: 'all 0.18s ease',
        position: 'relative',
        animation: isCritical ? 'pulse-glow 2.5s ease-in-out infinite' : 'none',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.transform = 'translateY(-1px)';
        e.currentTarget.style.boxShadow = `0 4px 16px ${colors.border}`;
      }}
      onMouseLeave={e => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = 'none';
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 6 }}>
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
            color: 'var(--text-pri)', letterSpacing: '0.02em',
            marginBottom: 4,
          }}>
            {server.name}
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 9,
            color: 'var(--text-muted)', letterSpacing: '0.08em',
          }}>
            {riskLabel(server.failProb)}
          </div>
        </div>

        {/* Prob badge + delta */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2, flexShrink: 0 }}>
          <div style={{
            background: colors.bg,
            border: `1px solid ${colors.border}`,
            borderRadius: 4,
            padding: '2px 6px',
            fontFamily: 'var(--font-mono)', fontWeight: 700,
            fontSize: 13, color: colors.text,
          }}>
            {server.failProb}%
          </div>
          {delta !== undefined && delta !== 0 && (
            <span
              title="Variação simulada — modelo em treinamento"
              style={{
                fontFamily: 'var(--font-mono)', fontSize: 9, fontWeight: 600,
                color: delta > 0 ? '#E8002D' : '#00e676',
                letterSpacing: '0.04em',
                cursor: 'help',
              }}
            >
              {delta > 0 ? `↑ +${delta}pp` : `↓ ${delta}pp`}
            </span>
          )}
        </div>
      </div>

      {/* Mini progress bar */}
      <div style={{
        height: 2, background: 'rgba(255,255,255,0.05)',
        borderRadius: 1, marginTop: 10, overflow: 'hidden',
      }}>
        <div style={{
          height: '100%', width: `${server.failProb}%`,
          background: `linear-gradient(90deg, ${colors.text}88, ${colors.text})`,
          borderRadius: 1, transition: 'width 0.6s ease',
        }} />
      </div>
    </div>
  );
}

export default function RiskHeatmap({ onSelectServer }) {
  const groups = getServersByProduct();

  return (
    <div style={{
      background: 'var(--surface1)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 20,
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 16,
      }}>
        <div>
          <div style={{
            fontFamily: 'var(--font-sans)', fontWeight: 600,
            fontSize: 13, color: 'var(--text-pri)',
          }}>
            Mapa de Risco por Servidor
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 10,
            color: 'var(--text-muted)', marginTop: 2,
          }}>
            Clique para detalhar — agrupado por produto
          </div>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          {[
            { label: 'CRÍTICO', color: 'var(--red)' },
            { label: 'ALTO',    color: 'var(--orange)' },
            { label: 'MÉDIO',   color: 'var(--yellow)' },
            { label: 'BAIXO',   color: 'var(--green)' },
          ].map(({ label, color }) => (
            <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <div style={{ width: 8, height: 8, borderRadius: 2, background: color, opacity: 0.8 }} />
              <span style={{
                fontFamily: 'var(--font-mono)', fontSize: 9,
                color: 'var(--text-muted)', letterSpacing: '0.08em',
              }}>
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {groups.map(({ product, servers }) => {
          const criticos = servers.filter(s => s.failProb >= 80).length;
          const alertas  = servers.filter(s => s.failProb >= 40 && s.failProb < 80).length;

          return (
            <div key={product}>
              {/* Group header with badges */}
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: 10,
                color: 'var(--text-muted)', letterSpacing: '0.12em',
                textTransform: 'uppercase', marginBottom: 8,
                display: 'flex', alignItems: 'center', gap: 8,
              }}>
                <span style={{ width: 16, height: 1, background: 'var(--border-md)', display: 'inline-block' }} />
                {product}

                {criticos > 0 && (
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 700,
                    color: '#E8002D',
                    background: 'rgba(232,0,45,0.12)',
                    border: '1px solid rgba(232,0,45,0.35)',
                    borderRadius: 3,
                    padding: '1px 6px',
                    letterSpacing: '0.08em',
                  }}>
                    {criticos} CRÍTICO{criticos > 1 ? 'S' : ''}
                  </span>
                )}

                {alertas > 0 && (
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 8, fontWeight: 700,
                    color: '#ff6d00',
                    background: 'rgba(255,109,0,0.1)',
                    border: '1px solid rgba(255,109,0,0.3)',
                    borderRadius: 3,
                    padding: '1px 6px',
                    letterSpacing: '0.08em',
                  }}>
                    {alertas} ALERTA{alertas > 1 ? 'S' : ''}
                  </span>
                )}

                <span style={{ height: 1, flex: 1, background: 'var(--border)', display: 'inline-block' }} />
              </div>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
                gap: 8,
              }}>
                {servers.map(server => (
                  <ServerCell
                    key={server.id}
                    server={server}
                    onClick={onSelectServer}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
