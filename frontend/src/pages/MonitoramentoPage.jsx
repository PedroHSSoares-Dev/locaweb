import { useState } from 'react';
import { useSearchParams, useNavigate, useLocation } from 'react-router-dom';
import { X } from 'lucide-react';
import { useDashboard } from '../context/DashboardContext';
import KpiCards from '../components/KpiCards';
import TimeSeriesChart from '../components/TimeSeriesChart';
import RiskHeatmap from '../components/RiskHeatmap';
import AlertsList from '../components/AlertsList';
import DrillDownPanel from '../components/DrillDownPanel';

export default function MonitoramentoPage() {
  const { horizon } = useDashboard();
  const [selectedServer, setSelectedServer] = useState(null);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();

  const filtroProduto = searchParams.get('produto');

  return (
    <div key={location.key} className="page-enter">
      <main style={{
        flex: 1,
        padding: '20px 24px 32px',
        display: 'flex', flexDirection: 'column', gap: 16,
        maxWidth: 1600,
        width: '100%',
        margin: '0 auto',
      }}>

        {/* Filter chip */}
        {filtroProduto && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: 10,
              color: 'var(--text-muted)', letterSpacing: '0.1em',
            }}>
              FILTRO ATIVO
            </span>
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 8,
              padding: '4px 10px', borderRadius: 4,
              background: 'rgba(232,0,45,0.10)',
              border: '1px solid rgba(232,0,45,0.3)',
              fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
              color: 'var(--red)',
            }}>
              Filtrando: {filtroProduto}
              <button
                onClick={() => navigate('/monitoramento')}
                style={{
                  display: 'flex', alignItems: 'center',
                  color: 'var(--red)', opacity: 0.7,
                  transition: 'opacity 0.15s',
                }}
                onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                onMouseLeave={e => e.currentTarget.style.opacity = '0.7'}
              >
                <X size={12} />
              </button>
            </span>
          </div>
        )}

        <KpiCards horizon={horizon} viewMode="geral" />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <TimeSeriesChart viewMode="geral" />
          <RiskHeatmap
            onSelectServer={setSelectedServer}
            filtroProduto={filtroProduto}
          />
        </div>

        <AlertsList
          horizon={horizon}
          viewMode="geral"
          onSelectServer={setSelectedServer}
          filtroProduto={filtroProduto}
        />
      </main>

      {selectedServer && (
        <DrillDownPanel
          server={selectedServer}
          horizon={horizon}
          onClose={() => setSelectedServer(null)}
        />
      )}
    </div>
  );
}
