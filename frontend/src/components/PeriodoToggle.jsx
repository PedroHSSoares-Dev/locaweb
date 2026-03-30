import { useBreakpoint } from '../hooks/useBreakpoint';

export default function PeriodoToggle({ value, onChange }) {
  const { isMobile } = useBreakpoint();
  const opcoes = ['MÊS', 'TRIMESTRE', 'ANO'];
  return (
    <div style={{
      display: 'flex',
      background: 'var(--surface3)',
      border: '1px solid var(--border-md)',
      borderRadius: 8,
      padding: 3,
      gap: 2,
    }}>
      {opcoes.map(op => {
        const ativo = value === op;
        return (
          <button
            key={op}
            onClick={() => onChange(op)}
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: isMobile ? 9 : 10,
              fontWeight: ativo ? 700 : 400,
              letterSpacing: '0.1em',
              color: ativo ? 'var(--bg)' : 'var(--text-sec)',
              background: ativo ? 'var(--text-pri)' : 'transparent',
              border: 'none',
              borderRadius: 6,
              padding: isMobile ? '4px 8px' : '5px 14px',
              cursor: 'pointer',
              transition: 'all 0.15s',
            }}
          >
            {op}
          </button>
        );
      })}
    </div>
  );
}
