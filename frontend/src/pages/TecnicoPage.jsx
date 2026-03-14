import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useDashboard } from '../context/DashboardContext';
import KpiCards from '../components/KpiCards';
import TimeSeriesChart from '../components/TimeSeriesChart';
import RiskHeatmap from '../components/RiskHeatmap';
import AlertsList from '../components/AlertsList';
import DrillDownPanel from '../components/DrillDownPanel';

export default function TecnicoPage() {
  const { horizon } = useDashboard();
  const [selectedServer, setSelectedServer] = useState(null);
  const location = useLocation();

  return (
    <div key={location.pathname} className="page-enter">
      <main style={{
        flex: 1,
        padding: '20px 24px 32px',
        display: 'flex', flexDirection: 'column', gap: 16,
        maxWidth: 1600,
        width: '100%',
        margin: '0 auto',
      }}>
        <KpiCards horizon={horizon} viewMode="tecnica" />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <TimeSeriesChart viewMode="tecnica" />
          <RiskHeatmap onSelectServer={setSelectedServer} />
        </div>

        <AlertsList
          horizon={horizon}
          viewMode="tecnica"
          onSelectServer={setSelectedServer}
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
