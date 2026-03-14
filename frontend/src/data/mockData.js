// ─── Seed reproducible random ────────────────────────────────────────────────
function seededRandom(seed) {
  let s = seed;
  return () => {
    s = (s * 16807 + 0) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

const rng = seededRandom(42);

// ─── Horizon multipliers ──────────────────────────────────────────────────────
export const horizonMultiplier = {
  '30min': { prob: 0.45, financial: 0.08 },
  '1h':    { prob: 0.60, financial: 0.15 },
  '6h':    { prob: 0.80, financial: 0.50 },
  '12h':   { prob: 0.90, financial: 0.75 },
  '24h':   { prob: 1.00, financial: 1.00 },
};

// ─── Feature importance profiles ─────────────────────────────────────────────
export const featureProfiles = {
  A: [
    { name: 'cpu_usage',       importance: 0.38 },
    { name: 'ram_usage',       importance: 0.22 },
    { name: 'disk_io',         importance: 0.16 },
    { name: 'net_errors',      importance: 0.12 },
    { name: 'swap_usage',      importance: 0.07 },
    { name: 'temp_sensor',     importance: 0.05 },
  ],
  B: [
    { name: 'packet_loss',     importance: 0.41 },
    { name: 'latency_p99',     importance: 0.27 },
    { name: 'net_errors',      importance: 0.15 },
    { name: 'bgp_flap',        importance: 0.10 },
    { name: 'cpu_usage',       importance: 0.04 },
    { name: 'uptime',          importance: 0.03 },
  ],
  C: [
    { name: 'disk_usage',      importance: 0.35 },
    { name: 'inode_pct',       importance: 0.24 },
    { name: 'disk_io',         importance: 0.18 },
    { name: 'ram_usage',       importance: 0.12 },
    { name: 'log_growth_rate', importance: 0.07 },
    { name: 'open_fds',        importance: 0.04 },
  ],
};

// ─── Products ─────────────────────────────────────────────────────────────────
const PRODUCTS = [
  'Hospedagem Compartilhada',
  'E-mail Pro',
  'Cloud Server',
  'DNS',
];

// ─── Raw server definitions (28 servers) ─────────────────────────────────────
// Sorted by failProb desc. Distribution:
//   Crítico (≥80): 4   — progressivo
//   Alerta  (55-79): 6  — spike
//   Atenção (30-54): 8  — ciclico
//   Normal  (<30): 10   — estavel
// Products: HOST(8), MAIL(7), CLOUD(8), DNS(5)
// Issues: queda_servidor(9)=HOST(4)+CLOUD(3)+MAIL(2)
//         falha_rede(9)=DNS(4)+CLOUD(3)+HOST(2)
//         esgotamento_recursos(10)=remaining
// DNS never has queda_servidor
const RAW_SERVERS = [
  // ── CRÍTICO ──────────────────────────────────────────────────────────────
  { id: 'srv-01', name: 'BRZ-HOST-01', product: 'Hospedagem Compartilhada', failProb: 94, probDelta: +13, pattern: 'progressivo', predictedIssue: 'queda_servidor',      featureProfile: 'A' },
  { id: 'srv-02', name: 'BRZ-CLOUD-03',product: 'Cloud Server',             failProb: 91, probDelta: +14, pattern: 'progressivo', predictedIssue: 'falha_rede',           featureProfile: 'B', latencyOverride: 340 },
  { id: 'srv-03', name: 'BRZ-MAIL-07', product: 'E-mail Pro',               failProb: 87, probDelta: +12, pattern: 'progressivo', predictedIssue: 'queda_servidor',      featureProfile: 'A' },
  { id: 'srv-04', name: 'BRZ-DNS-01',  product: 'DNS',                      failProb: 85, probDelta: +10, pattern: 'progressivo', predictedIssue: 'falha_rede',           featureProfile: 'B' },
  // ── ALERTA ───────────────────────────────────────────────────────────────
  { id: 'srv-05', name: 'BRZ-HOST-02', product: 'Hospedagem Compartilhada', failProb: 72, probDelta: +11, pattern: 'spike',       predictedIssue: 'queda_servidor',      featureProfile: 'A' },
  { id: 'srv-06', name: 'BRZ-CLOUD-01',product: 'Cloud Server',             failProb: 68, probDelta: +8,  pattern: 'spike',       predictedIssue: 'queda_servidor',      featureProfile: 'A' },
  { id: 'srv-07', name: 'BRZ-MAIL-01', product: 'E-mail Pro',               failProb: 64, probDelta: +9,  pattern: 'spike',       predictedIssue: 'queda_servidor',      featureProfile: 'A' },
  { id: 'srv-08', name: 'BRZ-DNS-02',  product: 'DNS',                      failProb: 62, probDelta: +15, pattern: 'spike',       predictedIssue: 'falha_rede',           featureProfile: 'B' },
  { id: 'srv-09', name: 'BRZ-HOST-03', product: 'Hospedagem Compartilhada', failProb: 58, probDelta: +7,  pattern: 'spike',       predictedIssue: 'falha_rede',           featureProfile: 'B' },
  { id: 'srv-10', name: 'BRZ-CLOUD-02',product: 'Cloud Server',             failProb: 55, probDelta: +6,  pattern: 'spike',       predictedIssue: 'falha_rede',           featureProfile: 'B', latencyOverride: 215 },
  // ── ATENÇÃO ───────────────────────────────────────────────────────────────
  { id: 'srv-11', name: 'BRZ-CLOUD-04',product: 'Cloud Server',             failProb: 51, probDelta: +4,  pattern: 'ciclico',     predictedIssue: 'queda_servidor',      featureProfile: 'A' },
  { id: 'srv-12', name: 'BRZ-MAIL-02', product: 'E-mail Pro',               failProb: 46, probDelta: +1,  pattern: 'ciclico',     predictedIssue: 'esgotamento_recursos', featureProfile: 'C' },
  { id: 'srv-13', name: 'BRZ-HOST-04', product: 'Hospedagem Compartilhada', failProb: 44, probDelta: +3,  pattern: 'ciclico',     predictedIssue: 'esgotamento_recursos', featureProfile: 'C', diskOverride: 92 },
  { id: 'srv-14', name: 'BRZ-MAIL-03', product: 'E-mail Pro',               failProb: 41, probDelta: -3,  pattern: 'ciclico',     predictedIssue: 'esgotamento_recursos', featureProfile: 'C' },
  { id: 'srv-15', name: 'BRZ-HOST-05', product: 'Hospedagem Compartilhada', failProb: 38, probDelta: -2,  pattern: 'ciclico',     predictedIssue: 'queda_servidor',      featureProfile: 'A' },
  { id: 'srv-16', name: 'BRZ-CLOUD-05',product: 'Cloud Server',             failProb: 37, probDelta: +5,  pattern: 'ciclico',     predictedIssue: 'queda_servidor',      featureProfile: 'A' },
  { id: 'srv-17', name: 'BRZ-CLOUD-06',product: 'Cloud Server',             failProb: 34, probDelta: +2,  pattern: 'ciclico',     predictedIssue: 'falha_rede',           featureProfile: 'B', latencyOverride: 220 },
  { id: 'srv-18', name: 'BRZ-HOST-06', product: 'Hospedagem Compartilhada', failProb: 33, probDelta: -6,  pattern: 'ciclico',     predictedIssue: 'falha_rede',           featureProfile: 'B' },
  // ── NORMAL ────────────────────────────────────────────────────────────────
  { id: 'srv-19', name: 'BRZ-DNS-03',  product: 'DNS',                      failProb: 28, probDelta: -3,  pattern: 'estavel',     predictedIssue: 'falha_rede',           featureProfile: 'B' },
  { id: 'srv-20', name: 'BRZ-MAIL-04', product: 'E-mail Pro',               failProb: 27, probDelta: -4,  pattern: 'estavel',     predictedIssue: 'esgotamento_recursos', featureProfile: 'C' },
  { id: 'srv-21', name: 'BRZ-DNS-04',  product: 'DNS',                      failProb: 24, probDelta: -3,  pattern: 'estavel',     predictedIssue: 'falha_rede',           featureProfile: 'B' },
  { id: 'srv-22', name: 'BRZ-CLOUD-07',product: 'Cloud Server',             failProb: 23, probDelta: -5,  pattern: 'estavel',     predictedIssue: 'esgotamento_recursos', featureProfile: 'C' },
  { id: 'srv-23', name: 'BRZ-HOST-07', product: 'Hospedagem Compartilhada', failProb: 21, probDelta: -4,  pattern: 'estavel',     predictedIssue: 'queda_servidor',      featureProfile: 'A' },
  { id: 'srv-24', name: 'BRZ-MAIL-05', product: 'E-mail Pro',               failProb: 18, probDelta: -5,  pattern: 'estavel',     predictedIssue: 'esgotamento_recursos', featureProfile: 'C' },
  { id: 'srv-25', name: 'BRZ-DNS-05',  product: 'DNS',                      failProb: 14, probDelta: -6,  pattern: 'estavel',     predictedIssue: 'esgotamento_recursos', featureProfile: 'C' },
  { id: 'srv-26', name: 'BRZ-HOST-08', product: 'Hospedagem Compartilhada', failProb: 12, probDelta: -5,  pattern: 'estavel',     predictedIssue: 'esgotamento_recursos', featureProfile: 'C' },
  { id: 'srv-27', name: 'BRZ-CLOUD-08',product: 'Cloud Server',             failProb: 11, probDelta: -6,  pattern: 'estavel',     predictedIssue: 'esgotamento_recursos', featureProfile: 'C' },
  { id: 'srv-28', name: 'BRZ-MAIL-06', product: 'E-mail Pro',               failProb: 9,  probDelta: -6,  pattern: 'estavel',     predictedIssue: 'esgotamento_recursos', featureProfile: 'C' },
];

function deriveStatus(failProb) {
  if (failProb >= 80) return 'crítico';
  if (failProb >= 40) return 'alerta';
  if (failProb >= 30) return 'atenção';
  return 'normal';
}

function horizonForProb(failProb, horizonLabel) {
  const map = { '30min': 0.5, '1h': 1, '6h': 6, '12h': 12, '24h': 24 };
  const hours = map[horizonLabel] || 6;
  if (failProb >= 80) return `~${Math.max(0.5, (hours * 0.15).toFixed(1))}h`;
  if (failProb >= 40) return `~${(hours * 0.5).toFixed(1)}h`;
  return `>${hours}h`;
}

export const servers = RAW_SERVERS.map((s) => {
  const r = () => rng();
  const cpuBase  = s.failProb * 0.85 + r() * 15;
  const ramBase  = s.failProb * 0.7  + r() * 25;
  const diskBase = s.diskOverride !== undefined
    ? s.diskOverride
    : s.failProb * 0.5 + r() * 30;
  const latBase  = s.latencyOverride !== undefined
    ? s.latencyOverride
    : s.failProb >= 80
      ? 180 + r() * 220
      : s.failProb >= 40
        ? 60 + r() * 120
        : 10 + r() * 50;

  return {
    ...s,
    cpu:            Math.min(99, Math.round(cpuBase)),
    ram:            Math.min(99, Math.round(ramBase)),
    disk:           Math.min(99, Math.round(diskBase)),
    latency:        Math.round(latBase),
    status:         deriveStatus(s.failProb),
    features:       featureProfiles[s.featureProfile],
  };
});

// ─── Deltas simulados (Visão Técnica) ─────────────────────────────────────────
export const serverDeltas = Object.fromEntries(
  servers.map(s => [
    s.id,
    {
      failProb: +(rng() * 6 - 3).toFixed(1),
      cpu:      +(rng() * 4 - 2).toFixed(1),
      ram:      +(rng() * 4 - 2).toFixed(1),
    },
  ])
);

// ─── Time series pattern generators ──────────────────────────────────────────
function patternProgressivo(base, i, points, r) {
  const trend = (i / (points - 1)) * 18;
  const noise = (r() - 0.5) * 6;
  return Math.min(100, Math.max(0, +(base - 10 + trend + noise).toFixed(1)));
}

function patternSpike(base, i, points, r) {
  const spikePeak = Math.floor(points * 0.65);
  const dist = Math.abs(i - spikePeak);
  const spike = dist < 4 ? (4 - dist) * 6 : 0;
  const noise = (r() - 0.5) * 7;
  return Math.min(100, Math.max(0, +(base - 8 + spike + noise).toFixed(1)));
}

function patternCiclico(base, i, _points, r) {
  const cycle = Math.sin(i * 0.52) * 14;
  const noise = (r() - 0.5) * 6;
  return Math.min(100, Math.max(0, +(base + cycle + noise).toFixed(1)));
}

function patternEstavel(base, i, _points, r) {
  const noise = (r() - 0.5) * 5;
  const drift = Math.sin(i * 0.18) * 3;
  return Math.min(100, Math.max(0, +(base + drift + noise).toFixed(1)));
}

function generateTimeSeries(server, points = 24) {
  const base = server.failProb;
  const patternFn = {
    progressivo: patternProgressivo,
    spike:       patternSpike,
    ciclico:     patternCiclico,
    estavel:     patternEstavel,
  }[server.pattern] ?? patternEstavel;

  return Array.from({ length: points }, (_, i) => patternFn(base, i, points, rng));
}

// 5 representative series: srv-01(progressivo), srv-04(progressivo/DNS),
// srv-05(spike), srv-02(progressivo/ciclico), srv-11(ciclico)
const TS_SERVERS = [
  servers.find(s => s.id === 'srv-01'),
  servers.find(s => s.id === 'srv-04'),
  servers.find(s => s.id === 'srv-05'),
  servers.find(s => s.id === 'srv-02'),
  servers.find(s => s.id === 'srv-11'),
];

export const timeSeriesData = Array.from({ length: 24 }, (_, i) => {
  const hourLabel = `${String(i).padStart(2, '0')}:00`;
  const entry = { hour: hourLabel };
  TS_SERVERS.forEach(s => {
    entry[s.id] = generateTimeSeries(s)[i];
  });
  return entry;
});

export const top3Servers = TS_SERVERS.slice(0, 3);

// ─── KPI helpers ─────────────────────────────────────────────────────────────
export function getKpis(horizonLabel) {
  const mult = horizonMultiplier[horizonLabel]?.prob ?? 1.0;
  const active   = servers.filter(s => s.failProb * mult >= 40);
  const maxProb  = Math.max(...servers.map(s => s.failProb));
  const map = { '30min': 0.5, '1h': 1, '6h': 6, '12h': 12, '24h': 24 };
  const h = map[horizonLabel] || 6;
  const nextIncident = +(h * (1 - maxProb / 100) * 1.2).toFixed(1);

  return {
    total:         servers.length,
    activeAlerts:  active.length,
    nextIncident:  Math.max(0.1, nextIncident),
  };
}

// ─── Grupo por produto ────────────────────────────────────────────────────────
export function getServersByProduct() {
  return PRODUCTS.map(product => ({
    product,
    servers: servers.filter(s => s.product === product),
  }));
}

// ─── Horizon → label helper ───────────────────────────────────────────────────
export { horizonForProb };

// ─── Impacto Financeiro ───────────────────────────────────────────────────────
// VALORES SIMULADOS PARA MVP — não representam dados reais da Locaweb
export const financialConfig = {
  revenuePerHourByProduct: {
    'Hospedagem Compartilhada': 18500,
    'E-mail Pro':               11200,
    'Cloud Server':             34000,
    'DNS':                       4800,
  },
  slaMultiplier:          2.4,
  churnRatePerIncident:   0.03,
  avgClientLTV:           1800,
  clientsPerProduct: {
    'Hospedagem Compartilhada': 42000,
    'E-mail Pro':               18500,
    'Cloud Server':              6200,
    'DNS':                      31000,
  },
  opsCostPerIncident: 12000,
};
