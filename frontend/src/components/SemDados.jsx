/**
 * SemDados — fallback terminal-style quando modelo não disponível.
 */
export default function SemDados({ mensagem }) {
  return (
    <div style={{
      minHeight: 150,
      background: 'var(--surface2)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      gap: 10, padding: '28px 20px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 24, color: 'var(--text-sec)', lineHeight: 1,
      }}>▣</div>
      <div style={{
        fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 700,
        color: 'var(--text-sec)', letterSpacing: '0.12em', textTransform: 'uppercase',
      }}>MODELO NÃO TREINADO</div>
      {mensagem && (
        <div style={{
          fontFamily: 'var(--font-mono)', fontSize: 10,
          color: 'var(--text-sec)',
          textAlign: 'center', maxWidth: 280, letterSpacing: '0.04em',
        }}>{mensagem}</div>
      )}
      <div style={{
        marginTop: 4,
        fontFamily: 'var(--font-mono)', fontSize: 10,
        color: 'var(--text-sec)',
        border: '1px solid var(--border-md)', borderRadius: 3,
        padding: '3px 10px', letterSpacing: '0.08em',
      }}>[EXECUTAR_NOTEBOOK]</div>
    </div>
  );
}
