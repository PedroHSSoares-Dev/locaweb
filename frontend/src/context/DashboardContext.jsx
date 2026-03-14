import { createContext, useContext, useState } from 'react';

const DashboardContext = createContext();

export function DashboardProvider({ children }) {
  const [filtroAtivo, setFiltroAtivo] = useState(null); // null | produto | grupo | categoria
  const [viewMode, setViewMode] = useState('geral');
  return (
    <DashboardContext.Provider value={{ filtroAtivo, setFiltroAtivo, viewMode, setViewMode }}>
      {children}
    </DashboardContext.Provider>
  );
}

export const useDashboard = () => useContext(DashboardContext);
