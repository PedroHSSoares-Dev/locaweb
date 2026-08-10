import { useContext } from 'react';
import { DashboardContext } from '../context/dashboard-context';

export function useDashboard() {
  const value = useContext(DashboardContext);
  if (!value) throw new Error('useDashboard deve ser usado dentro de DashboardProvider.');
  return value;
}
