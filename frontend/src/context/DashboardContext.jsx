import { useCallback, useMemo, useState } from 'react';
import { DashboardContext } from './dashboard-context';

const INITIAL_FILTERS = {
  '/gestao': { periodo: 'ANO', prioridade: 'AMBOS' },
  '/monitoramento': { visualizacao: 'VOLUME' },
  '/operacoes': { status: 'TODOS' },
  '/tecnico': { clusters: 'TODOS' },
  '/modelos': {},
};

export function DashboardProvider({ children }) {
  const [filtroAtivo, setFiltroAtivo] = useState(null); // null | produto | grupo | categoria
  const [viewMode, setViewMode] = useState('geral');
  const [filtersByRoute, setFiltersByRoute] = useState(INITIAL_FILTERS);

  const updateDashboardFilter = useCallback((route, key, value) => {
    setFiltersByRoute((current) => ({
      ...current,
      [route]: { ...current[route], [key]: String(value) },
    }));
  }, []);

  const value = useMemo(() => ({
    filtroAtivo,
    setFiltroAtivo,
    viewMode,
    setViewMode,
    filtersByRoute,
    updateDashboardFilter,
  }), [filtroAtivo, filtersByRoute, updateDashboardFilter, viewMode]);

  return (
    <DashboardContext.Provider value={value}>
      {children}
    </DashboardContext.Provider>
  );
}
