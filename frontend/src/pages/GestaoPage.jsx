import {
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ArrowRight, CalendarClock, ShieldAlert, Target } from 'lucide-react';
import PeriodoToggle from '../components/PeriodoToggle';
import SemDados from '../components/SemDados';
import { kpiAtingimento, olaTargets, volumeMensal2025 } from '../data/mockData';
import { useApi } from '../hooks/useApi';
import { useBreakpoint } from '../hooks/useBreakpoint';
import { useDashboard } from '../hooks/useDashboard';
import './DashboardPages.css';

const PERIOD_LABELS = {
  'MÊS': 'Dezembro de 2025',
  'TRIMESTRE': '4º trimestre de 2025',
  'ANO': 'Ano de 2025',
};

const PERIOD_API = { 'MÊS': 'mes', 'TRIMESTRE': 'trimestre', 'ANO': 'ano' };
const PERIOD_MONTHS = { 'MÊS': 1, 'TRIMESTRE': 3, 'ANO': 12 };
const PRIORITY_COLOR = { P2: 'var(--teal)', P3: 'var(--yellow)' };

function filterHistory(data, period) {
  if (period === 'MÊS') return data.slice(-1);
  if (period === 'TRIMESTRE') return data.slice(-3);
  return data;
}

function fallbackRange(priority, period) {
  const annual = olaTargets[priority].metaViolacoesAno;
  const months = PERIOD_MONTHS[period];
  return {
    min: Math.round(annual.min * months / 12),
    max: Math.round(annual.max * months / 12),
  };
}

function PageHeader({ period, onPeriodChange }) {
  const { isMobile } = useBreakpoint();
  return (
    <header className="dashboard-page-header">
      <div>
        <h1>Centro de Gestão</h1>
        {!isMobile && <p>Visão executiva · risco OLA · capacidade prevista</p>}
      </div>
      {!isMobile && <PeriodoToggle value={period} onChange={onPeriodChange} />}
    </header>
  );
}

function Module({ n, title, sub, children, action }) {
  return (
    <section className="dashboard-module">
      <header className="dashboard-module__header">
        <div>
          <span>MÓDULO {String(n).padStart(2, '0')}</span>
          <h2>{title}</h2>
          {sub && <p>{sub}</p>}
        </div>
        {action}
      </header>
      <div className="dashboard-module__body">{children}</div>
    </section>
  );
}

function OlaCard({ priority, data, period }) {
  const fallback = fallbackRange(priority, period);
  const violations = data?.violacoesAno ?? kpiAtingimento[priority].violacoesAno ?? 0;
  const reference = data?.metaAnual ?? Math.round((fallback.min + fallback.max) / 2);
  const min = data?.metaMin ?? fallback.min;
  const max = data?.metaMax ?? fallback.max;
  const used = data?.pctUtilizado ?? (reference ? violations / reference * 100 : 0);
  const over = violations > max;
  const color = over ? 'var(--red)' : used >= 85 ? 'var(--orange)' : 'var(--green)';
  const remaining = max - violations;

  return (
    <article className="ola-summary" style={{ '--priority-color': PRIORITY_COLOR[priority], '--status-color': color }}>
      <div className="ola-summary__topline">
        <span>{priority} · OLA {priority === 'P2' ? '4h' : '12h'}</span>
        <strong>{over ? 'FORA DA FAIXA' : 'DENTRO DA FAIXA'}</strong>
      </div>
      <div className="ola-summary__numbers">
        <strong>{violations}</strong>
        <div>
          <span>violações</span>
          <small>faixa de negócio {min}–{max} · referência {reference}</small>
        </div>
      </div>
      <div className="ola-summary__progress" aria-label={`${used.toFixed(1)}% da referência consumida`}>
        <i style={{ width: `${Math.min(100, used)}%` }} />
      </div>
      <footer>
        <span>{used.toFixed(1)}% da referência</span>
        <span>{remaining >= 0 ? `${remaining} até o limite superior` : `${Math.abs(remaining)} acima do limite superior`}</span>
      </footer>
    </article>
  );
}

function ForecastCard({ label, data, available, color }) {
  return (
    <article className="forecast-summary" style={{ '--forecast-color': color }}>
      <span>{label}</span>
      <strong>{available ? data?.total ?? '—' : '—'}</strong>
      <p>{available && data?.p2 != null ? `P2 ${data.p2} · P3 ${data.p3}` : 'Detalhamento indisponível'}</p>
      {available && data?.reconciliado ? <small className="forecast-summary__reconciled">P2/P3 reconciliados ao Total</small> : null}
    </article>
  );
}

export default function GestaoPage() {
  const { isMobile, isTablet } = useBreakpoint();
  const { filtersByRoute, updateDashboardFilter } = useDashboard();
  const period = filtersByRoute['/gestao']?.periodo || 'ANO';
  const priorityFilter = filtersByRoute['/gestao']?.prioridade || 'AMBOS';

  const { data: d1, loading: forecastLoading, disponivel: d1Available } = useApi('/previsoes/d1');
  const { data: d7, disponivel: d7Available } = useApi('/previsoes/d7');
  const { data: kpi, loading: kpiLoading, disponivel: kpiAvailable } = useApi('/kpi', {
    periodo: PERIOD_API[period],
  });

  const p2 = kpiAvailable ? kpi.P2 : kpiAtingimento.P2;
  const p3 = kpiAvailable ? kpi.P3 : kpiAtingimento.P3;
  const history = filterHistory(volumeMensal2025, period).map((item) => ({
    ...item,
    violP2: priorityFilter === 'P3' ? null : item.violP2,
    violP3: priorityFilter === 'P2' ? null : item.violP3,
  }));
  const p2Critical = (p2?.violacoesAno ?? 0) > (p2?.metaMax ?? fallbackRange('P2', period).max);
  const p3Critical = (p3?.violacoesAno ?? 0) > (p3?.metaMax ?? fallbackRange('P3', period).max);
  const outlook = p2Critical || p3Critical ? 'Atenção executiva necessária' : 'Operação dentro da faixa esperada';

  return (
    <div className="dashboard-page">
      <PageHeader period={period} onPeriodChange={(value) => updateDashboardFilter('/gestao', 'periodo', value)} />
      <main className="dashboard-page__content">
        {isMobile && <PeriodoToggle value={period} onChange={(value) => updateDashboardFilter('/gestao', 'periodo', value)} />}

        <section className="executive-brief" aria-labelledby="executive-brief-title">
          <div className="executive-brief__signal"><ShieldAlert size={18} /></div>
          <div className="executive-brief__copy">
            <span>NORTE EXECUTIVO · {PERIOD_LABELS[period]}</span>
            <h2 id="executive-brief-title">{outlook}</h2>
            <p>
              {p2Critical
                ? 'P2 ultrapassou a faixa de negócio e deve concentrar a resposta operacional.'
                : 'P2 permanece dentro da faixa de negócio.'}{' '}
              {p3Critical ? 'P3 também exige escalação.' : 'P3 permanece controlado no período.'}
            </p>
          </div>
          <div className="executive-brief__actions">
            <span><Target size={14} /> Priorizar P2</span>
            <span><CalendarClock size={14} /> Revisão semanal</span>
            <span><ArrowRight size={14} /> Escalar ao exceder o limite</span>
          </div>
        </section>

        <Module n={1} title="Metas OLA e consumo" sub={`Faixas anuais de negócio distribuídas · ${PERIOD_LABELS[period]}`}>
          {kpiLoading ? <div className="skeleton" style={{ height: 210 }} /> : (
            <div className="ola-summary-grid">
              <OlaCard priority="P2" data={p2} period={period} />
              <OlaCard priority="P3" data={p3} period={period} />
            </div>
          )}
        </Module>

        <div className="dashboard-split" style={{ gridTemplateColumns: isMobile || isTablet ? '1fr' : '0.82fr 1.18fr' }}>
          <Module n={2} title="Capacidade prevista" sub={`${(d1?.modelo_usado ?? 'modelo').toUpperCase()} · horizonte operacional D+1 e D+7`}>
            {forecastLoading ? <div className="skeleton" style={{ height: 220 }} /> : !d1Available ? (
              <SemDados mensagem="Previsão indisponível" />
            ) : (
              <div className="forecast-summary-grid">
                <ForecastCard label="Próximo dia · D+1" data={d1} available={d1Available} color="var(--orange)" />
                <ForecastCard label="Próxima semana · D+7" data={d7} available={d7Available} color="var(--yellow)" />
              </div>
            )}
          </Module>

          <Module
            n={3}
            title="Histórico de violações"
            sub={`P2 e P3 por mês · ${PERIOD_LABELS[period]}`}
            action={(
              <div className="priority-segmented" aria-label="Filtrar prioridade">
                {['P2', 'P3', 'AMBOS'].map((item) => (
                  <button
                    key={item}
                    type="button"
                    aria-pressed={priorityFilter === item}
                    onClick={() => updateDashboardFilter('/gestao', 'prioridade', item)}
                  >{item}</button>
                ))}
              </div>
            )}
          >
            <div style={{ width: '100%', minWidth: 0, minHeight: 300 }}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={history} margin={{ top: 12, right: 10, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="mes" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickLine={false} axisLine={{ stroke: 'var(--border)' }} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: 'var(--surface3)', border: '1px solid var(--border-md)', borderRadius: 8, fontSize: 12 }} />
                  <ReferenceLine y={Math.max(1, Math.round((p2?.metaAnual ?? 37) / PERIOD_MONTHS[period]))} stroke="var(--teal)" strokeDasharray="4 4" opacity={0.45} />
                  <Bar dataKey="violP2" name="P2" fill="var(--teal)" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="violP3" name="P3" fill="var(--yellow)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Module>
        </div>
      </main>
    </div>
  );
}
