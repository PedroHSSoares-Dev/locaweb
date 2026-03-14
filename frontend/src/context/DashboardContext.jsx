import { createContext, useContext, useState } from 'react';

const DashboardContext = createContext();

export function DashboardProvider({ children }) {
  const [horizon, setHorizon] = useState('6h');
  const [viewMode, setViewMode] = useState('geral');
  return (
    <DashboardContext.Provider value={{ horizon, setHorizon, viewMode, setViewMode }}>
      {children}
    </DashboardContext.Provider>
  );
}

export const useDashboard = () => useContext(DashboardContext);
