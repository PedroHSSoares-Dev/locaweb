import { useState } from 'react';
import './index.css';
import Topbar from './components/Topbar';
import KpiCards from './components/KpiCards';
import RiskHeatmap from './components/RiskHeatmap';
import AlertsList from './components/AlertsList';
import TimeSeriesChart from './components/TimeSeriesChart';
import DrillDownPanel from './components/DrillDownPanel';
import FinancialImpact from './components/FinancialImpact';
import { servers } from './data/mockData';

export default function App() {
  const [horizon, setHorizon] = useState('6h');
  const [viewMode, setViewMode] = useState('geral');
  const [selectedServer, setSelectedServer] = useState(null);
  const [activePage, setActivePage] = useState('dashboard');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Topbar
        horizon={horizon}
        setHorizon={setHorizon}
        viewMode={viewMode}
        setViewMode={setViewMode}
        activePage={activePage}
        onNavigate={setActivePage}
      />

      {activePage === 'dashboard' && (
        <div key="dashboard" className="page-enter">
          <main style={{
            flex: 1,
            padding: '20px 24px 32px',
            display: 'flex', flexDirection: 'column', gap: 16,
            maxWidth: 1600,
            width: '100%',
            margin: '0 auto',
          }}>
            <KpiCards horizon={horizon} viewMode={viewMode} />

            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 16,
            }}>
              <TimeSeriesChart viewMode={viewMode} />
              <RiskHeatmap onSelectServer={setSelectedServer} />
            </div>

            <AlertsList
              horizon={horizon}
              viewMode={viewMode}
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
      )}

      {activePage === 'financial' && (
        <div key="financial" className="page-enter">
          <main style={{
            flex: 1,
            padding: '20px 24px 32px',
            maxWidth: 1600,
            width: '100%',
            margin: '0 auto',
          }}>
            <FinancialImpact
              servers={servers}
              horizon={horizon}
              viewMode={viewMode}
            />
          </main>
        </div>
      )}
    </div>
  );
}
