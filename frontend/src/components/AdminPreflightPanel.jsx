import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle2, LoaderCircle, RefreshCw, Rocket } from 'lucide-react';

const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/$/, '');

export default function AdminPreflightPanel({ token, onUnauthorized }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const run = useCallback(async (signal) => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API_BASE}/admin/preflight`, {
        headers: { Authorization: `Bearer ${token}` }, signal,
      });
      const body = await response.json().catch(() => ({}));
      if (response.status === 401) {
        onUnauthorized();
        return;
      }
      if (!response.ok) throw new Error(body.detail || `Falha HTTP ${response.status}`);
      setData(body);
    } catch (requestError) {
      if (requestError.name !== 'AbortError') setError(requestError.message || 'Preflight indisponível.');
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [onUnauthorized, token]);

  useEffect(() => {
    const controller = new AbortController();
    run(controller.signal);
    return () => controller.abort();
  }, [run]);

  return (
    <section className="admin-preflight" aria-labelledby="preflight-title">
      <header className="admin-usage__head">
        <div className="admin-section-heading">
          <span className="admin-section-heading__index">03</span>
          <div><h2 id="preflight-title">Preflight de release</h2><p>Artefatos, modelos, banco, fila e assistente verificados sem expor segredos.</p></div>
        </div>
        <button type="button" className="admin-icon-button" onClick={() => run()} disabled={loading} aria-label="Executar preflight novamente">
          <RefreshCw size={15} className={loading ? 'admin-spin' : ''} />
        </button>
      </header>

      {loading && !data ? <div className="admin-preflight__loading"><LoaderCircle className="admin-spin" size={20} /> VALIDANDO RELEASE…</div>
        : error ? <div className="admin-preflight__error"><AlertTriangle size={21} /><div><strong>PRECHECK NÃO CONCLUÍDO</strong><span>{error}</span></div><button type="button" onClick={() => run()}>TENTAR NOVAMENTE</button></div>
          : <>
            <div className={`admin-preflight__verdict admin-preflight__verdict--${data?.status || 'blocked'}`}>
              {data?.status === 'ready' ? <Rocket size={19} /> : <AlertTriangle size={19} />}
              <div><strong>{data?.status === 'ready' ? 'READY PARA DEMONSTRAÇÃO' : 'RELEASE BLOQUEADO'}</strong><span>{data?.passed || 0} de {data?.total || 0} verificações aprovadas</span></div>
            </div>
            <div className="admin-preflight__checks">{data?.checks?.map((item) => (
              <article key={item.name} className={item.ok ? 'is-ok' : 'is-failed'}>
                {item.ok ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                <div><strong>{item.name.replaceAll('_', ' ').toUpperCase()}</strong><span>{item.detail}</span></div>
              </article>
            ))}</div>
          </>}
    </section>
  );
}
