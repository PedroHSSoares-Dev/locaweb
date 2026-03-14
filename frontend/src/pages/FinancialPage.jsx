import { useLocation } from 'react-router-dom';
import { useDashboard } from '../context/DashboardContext';
import FinancialImpact from '../components/FinancialImpact';
import { servers } from '../data/mockData';

export default function FinancialPage() {
  const { horizon } = useDashboard();
  const location = useLocation();

  return (
    <div key={location.pathname} className="page-enter">
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
          viewMode="geral"
        />
      </main>
    </div>
  );
}
