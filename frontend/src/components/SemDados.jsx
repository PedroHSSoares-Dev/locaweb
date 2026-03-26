/**
 * SemDados — Fallback para quando dados de modelo não estão disponíveis.
 * Exibido enquanto notebooks pendentes não gerarem seus outputs/*.json.
 */
export default function SemDados({ mensagem }) {
  return (
    <div style={{
      minHeight: 120,
      background: 'var(--surface2)',
      borderRadius: 8,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      padding: '24px 16px',
    }}>
      <div style={{
        width: 36, height: 36,
        borderRadius: '50%',
        background: 'var(--surface3)',
        border: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'var(--font-mono)',
        fontSize: 16,
        color: 'var(--text-muted)',
      }}>—</div>
      <div style={{
        fontFamily: 'var(--font-sans)',
        fontSize: 12,
        fontWeight: 500,
        color: 'var(--text-muted)',
      }}>Sem dados disponíveis</div>
      {mensagem && (
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 10,
          color: 'var(--text-muted)',
          opacity: 0.7,
          textAlign: 'center',
          maxWidth: 280,
        }}>{mensagem}</div>
      )}
    </div>
  );
}
