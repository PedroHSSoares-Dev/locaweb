import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, LabelList,
} from 'recharts';
import { X, ExternalLink, Cpu, HardDrive, Database, Wifi, Activity } from 'lucide-react';
import { horizonForProb } from '../data/mockData';

const ISSUE_LABELS = {
  queda_servidor: 'Queda de Servidor',
  falha_rede: 'Falha de Rede / Conectividade',
  esgotamento_recursos: 'Esgotamento de Recursos',
};

function riskColor(prob) {
  if (prob >= 80) return 'var(--red)';
  if (prob >= 60) return 'var(--orange)';
  if (prob >= 40) return 'var(--yellow)';
  return 'var(--green)';
}

function MetricBar({ label, value, max = 100, icon: Icon, unit = '%' }) {
  const color = value >= 85 ? 'var(--red)' : value >= 70 ? 'var(--orange)' : value >= 50 ? 'var(--yellow)' : 'var(--green)';
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {Icon && <Icon size={12} color='var(--text-muted)' />}
          <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-sec)' }}>{label}</span>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 13, color }}>
          {value}{unit}
        </span>
      </div>
      <div style={{ height: 4, background: 'var(--surface3)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${Math.min(100, (value / max) * 100)}%`,
          background: `linear-gradient(90deg, ${color}88, ${color})`,
          borderRadius: 2,
          transition: 'width 0.8s cubic-bezier(0.16,1,0.3,1)',
        }} />
      </div>
    </div>
  );
}

function featureImportance(server) {
  const base = server.failProb / 100;
  const features = [
    { name: 'CPU Load',  importance: +(base * 0.32 + Math.random() * 0.08).toFixed(3) },
    { name: 'RAM Usage', importance: +(base * 0.25 + Math.random() * 0.07).toFixed(3) },
    { name: 'Disk I/O',  importance: +(base * 0.20 + Math.random() * 0.06).toFixed(3) },
    { name: 'Latência',  importance: +(base * 0.15 + Math.random() * 0.05).toFixed(3) },
    { name: 'Erros HTTP',importance: +(base * 0.08 + Math.random() * 0.04).toFixed(3) },
  ];
  const total = features.reduce((a, f) => a + f.importance, 0);
  return features
    .map(f => ({ ...f, importance: +(f.importance / total).toFixed(3) }))
    .sort((a, b) => b.importance - a.importance);
}

// ─── Group features < 5% into "Outros", derive opacity per bar ───────────────
function processFeatures(features) {
  const sorted = [...features].sort((a, b) => b.importance - a.importance);
  const main   = sorted.filter(f => f.importance >= 0.05);
  const others = sorted.filter(f => f.importance < 0.05);
  if (others.length > 0) {
    main.push({ name: 'Outros', importance: others.reduce((s, f) => s + f.importance, 0) });
  }
  const max = main[0].importance;
  return main.map(f => ({ ...f, opacity: 0.2 + 0.8 * (f.importance / max) }));
}

function FeatureTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--surface3)',
      border: '1px solid var(--border-md)',
      borderRadius: 4, padding: '6px 10px',
      fontFamily: 'var(--font-mono)', fontSize: 10,
      color: 'var(--text-pri)',
    }}>
      {(payload[0].value * 100).toFixed(1)}%
    </div>
  );
}

export default function DrillDownPanel({ server, horizon, onClose }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (server) requestAnimationFrame(() => setVisible(true));
    else setVisible(false);
  }, [server]);

  const handleClose = () => {
    setVisible(false);
    setTimeout(onClose, 220);
  };

  if (!server) return null;

  const color    = riskColor(server.failProb);
  const features = processFeatures(server.features ?? featureImportance(server));

  return (
    <>
      {/* Overlay */}
      <div onClick={handleClose} style={{
        position: 'fixed', inset: 0, zIndex: 200,
        background: 'rgba(0,0,0,0.6)',
        backdropFilter: 'blur(2px)',
        opacity: visible ? 1 : 0,
        transition: 'opacity 0.22s ease',
      }} />

      {/* Panel */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 201,
        width: 380,
        background: 'var(--surface1)',
        borderLeft: '1px solid var(--border-md)',
        display: 'flex', flexDirection: 'column',
        transform: visible ? 'translateX(0)' : 'translateX(40px)',
        opacity: visible ? 1 : 0,
        transition: 'transform 0.22s cubic-bezier(0.16,1,0.3,1), opacity 0.22s ease',
        overflowY: 'auto',
      }}>

        {/* Header */}
        <div style={{
          padding: '18px 20px 14px',
          borderBottom: '1px solid var(--border)',
          position: 'sticky', top: 0,
          background: 'var(--surface1)', zIndex: 1,
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
            <div>
              <div style={{
                fontFamily: 'var(--font-mono)', fontWeight: 700,
                fontSize: 14, color: 'var(--text-pri)', marginBottom: 4,
              }}>
                {server.name}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: 'var(--text-muted)' }}>
                  {server.product}
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: 10,
                  color, padding: '1px 6px',
                  background: `${color}18`, border: `1px solid ${color}44`,
                  borderRadius: 3, letterSpacing: '0.06em',
                }}>
                  {server.status.toUpperCase()}
                </span>
              </div>
            </div>
            <button onClick={handleClose} style={{
              padding: 6, borderRadius: 6,
              color: 'var(--text-sec)', border: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', transition: 'all 0.15s',
            }}
              onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-pri)'; e.currentTarget.style.borderColor = 'var(--border-md)'; }}
              onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-sec)'; e.currentTarget.style.borderColor = 'var(--border)'; }}
            >
              <X size={14} />
            </button>
          </div>

          {/* Prob highlight */}
          <div style={{
            marginTop: 14, padding: '12px 16px',
            background: `${color}0d`, border: `1px solid ${color}33`,
            borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <div>
              <div style={{ fontFamily: 'var(--font-sans)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>
                PROBABILIDADE DE FALHA
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 28, color, lineHeight: 1 }}>
                {server.failProb}%
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontFamily: 'var(--font-sans)', fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>
                HORIZONTE
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: 14, color: 'var(--text-pri)' }}>
                {horizonForProb(server.failProb, horizon)}
              </div>
            </div>
          </div>
        </div>

        {/* Body */}
        <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Prediction type */}
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10,
              color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: 10,
            }}>
              TIPO DE FALHA PREDITA
            </div>
            <div style={{
              padding: '10px 14px',
              background: 'var(--surface2)', border: '1px solid var(--border)',
              borderRadius: 6, fontFamily: 'var(--font-sans)', fontSize: 12,
              color: 'var(--text-pri)', fontWeight: 500,
            }}>
              {ISSUE_LABELS[server.predictedIssue] || server.predictedIssue}
            </div>
          </div>

          {/* Metrics */}
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10,
              color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: 12,
            }}>
              MÉTRICAS ATUAIS
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <MetricBar label="CPU"     value={server.cpu}     icon={Cpu} />
              <MetricBar label="RAM"     value={server.ram}     icon={Database} />
              <MetricBar label="Disco"   value={server.disk}    icon={HardDrive} />
              <MetricBar label="Latência" value={server.latency} max={500} icon={Wifi} unit="ms" />
            </div>
          </div>

          {/* Feature importance */}
          <div>
            <div style={{
              fontFamily: 'var(--font-mono)', fontSize: 10,
              color: 'var(--text-muted)', letterSpacing: '0.12em', marginBottom: 4,
            }}>
              IMPORTÂNCIA DE FEATURES (ML)
            </div>
            <div style={{
              fontFamily: 'var(--font-sans)', fontSize: 10,
              color: 'var(--text-muted)', marginBottom: 12,
            }}>
              Contribuição de cada métrica para a predição
            </div>

            <ResponsiveContainer width="100%" height={features.length * 26 + 20}>
              <BarChart
                data={features}
                layout="vertical"
                margin={{ top: 0, right: 48, bottom: 0, left: 56 }}
                barSize={9}
              >
                <XAxis
                  type="number" domain={[0, 1]} hide
                />
                <YAxis
                  type="category" dataKey="name" width={52}
                  tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--text-sec)' }}
                  tickLine={false} axisLine={false}
                />
                <Tooltip content={<FeatureTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Bar dataKey="importance" radius={[0, 3, 3, 0]}>
                  {features.map((f, i) => (
                    <Cell key={i} fill="#E8002D" fillOpacity={f.opacity} />
                  ))}
                  <LabelList
                    dataKey="importance"
                    position="right"
                    formatter={v => (v * 100).toFixed(0) + '%'}
                    style={{ fill: '#f0f0f0', fontSize: 11, fontFamily: 'var(--font-mono)' }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Log button */}
          <button style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
            padding: '10px 16px', borderRadius: 6,
            fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600,
            color: 'var(--text-sec)', border: '1px solid var(--border-md)',
            background: 'var(--surface2)', transition: 'all 0.15s',
            letterSpacing: '0.06em', marginBottom: 4,
          }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-pri)'; e.currentTarget.style.background = 'var(--surface3)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-sec)'; e.currentTarget.style.background = 'var(--surface2)'; }}
          >
            <Activity size={12} />
            Ver logs completos
            <ExternalLink size={11} style={{ opacity: 0.5 }} />
          </button>

          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: 9,
            color: 'var(--text-muted)', textAlign: 'center', letterSpacing: '0.06em',
          }}>
            ID: {server.id} · Modelo: GBM v2.4.1
          </div>
        </div>
      </div>
    </>
  );
}
