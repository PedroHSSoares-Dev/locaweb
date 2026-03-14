// ─── mockData.js — Predictfy × Locaweb ───────────────────────────────────────
// Dados baseados no dataset ITSM real (LW-DATASET.xlsx)
// 122.543 incidentes · jan/2023–dez/2025 · subset KPI: 25.600 (P2+P3)
// SUBSTITUIR por outputs dos modelos ML quando prontos (outputs/*.json)
// ─────────────────────────────────────────────────────────────────────────────

// ─── Metas OLA anuais (Locaweb) ───────────────────────────────────────────────
export const olaTargets = {
  P2: { limiteHoras: 4,  metaViolacoesAno: { min: 36, max: 39 } },
  P3: { limiteHoras: 12, metaViolacoesAno: { min: 231, max: 263 } },
};

// ─── Volume acumulado de violações em 2025 (dado real) ───────────────────────
export const violacoesReais2025 = {
  P2: 42,  // total ano 2025 — acima da meta (36–39)
  P3: 196, // total ano 2025 — dentro da meta (231–263)
  porMes: {
    P2: [4,4,3,2,6,3,6,3,2,2,6,1],
    P3: [19,21,16,10,15,28,23,14,9,9,15,17],
  },
};

// ─── KPI de atingimento (simulado modelo — substituir por kpi_atingimento.json)
// pctAtingimento baseado na PROJEÇÃO Prophet (previsaoFechamento), não nos reais:
//   P2: 39/47 * 100 = 83%   P3: 263/210 * 100 = 125% → cap visual 118% (razoável)
export const kpiAtingimento = {
  P2: {
    violacoesAno:       42,   // real 2025
    metaMax:            39,
    pctAtingimento:     83,   // baseado em projeção 47 (39/47*100)
    tendencia:          'piorando',
    previsaoFechamento: 47,
  },
  P3: {
    violacoesAno:       196,  // real 2025
    metaMax:            263,
    pctAtingimento:     118,  // baseado em projeção 210 (263/210*100, cap display)
    tendencia:          'estavel',
    previsaoFechamento: 210,
  },
};

// ─── Produtos (anonimizados — pedir dicionário ao Douglas) ───────────────────
export const produtos = [
  { id: 'lhco', total: 8165, violacoes: 55, taxaViolacao: 0.67 },
  { id: 'lcem', total: 3688, violacoes: 25, taxaViolacao: 0.68 },
  { id: 'lsin', total: 3259, violacoes: 63, taxaViolacao: 1.93 },
  { id: 'lhvp', total: 1891, violacoes: 14, taxaViolacao: 0.74 },
  { id: 'lrev', total: 1833, violacoes:  9, taxaViolacao: 0.49 },
  { id: 'lcsi', total: 1064, violacoes:  2, taxaViolacao: 0.19 },
  { id: 'lsaa', total:  572, violacoes:  8, taxaViolacao: 1.40 },
  { id: 'lcho', total:  512, violacoes:  3, taxaViolacao: 0.59 },
  { id: 'lrel', total:  508, violacoes:  5, taxaViolacao: 0.98 },
  { id: 'lrdo', total:  490, violacoes:  8, taxaViolacao: 1.63 },
];

// ─── Grupos de atendimento ────────────────────────────────────────────────────
export const grupos = [
  { id: 'Team14', total: 8973, violacoes:  10, taxaViolacao: 0.11 },
  { id: 'Team11', total: 8702, violacoes: 114, taxaViolacao: 1.31 },
  { id: 'Team05', total: 3628, violacoes:  13, taxaViolacao: 0.36 },
  { id: 'Team09', total: 2058, violacoes:  56, taxaViolacao: 2.72 },
  { id: 'Team17', total:  484, violacoes:   4, taxaViolacao: 0.83 },
  { id: 'Team03', total:  415, violacoes:  12, taxaViolacao: 2.89 },
  { id: 'Team12', total:  395, violacoes:   8, taxaViolacao: 2.03 },
  { id: 'Team02', total:  251, violacoes:   4, taxaViolacao: 1.59 },
  { id: 'Team07', total:  179, violacoes:  16, taxaViolacao: 8.94 }, // ⚠️ maior taxa
  { id: 'Team10', total:  159, violacoes:   1, taxaViolacao: 0.63 },
];

// ─── Categorias ───────────────────────────────────────────────────────────────
export const categorias = [
  { id: 'cat71',  total: 3584, violacoes: 26, taxaViolacao: 0.73 },
  { id: 'cat85',  total: 3506, violacoes: 33, taxaViolacao: 0.94 },
  { id: 'cat31',  total: 2226, violacoes: 46, taxaViolacao: 2.07 },
  { id: 'cat76',  total: 2218, violacoes:  7, taxaViolacao: 0.32 },
  { id: 'cat77',  total: 1599, violacoes: 11, taxaViolacao: 0.69 },
  { id: 'cat73',  total: 1259, violacoes:  8, taxaViolacao: 0.64 },
  { id: 'cat91',  total: 1188, violacoes: 11, taxaViolacao: 0.93 },
  { id: 'cat137', total:  832, violacoes:  4, taxaViolacao: 0.48 },
  { id: 'cat103', total:  672, violacoes: 11, taxaViolacao: 1.64 },
  { id: 'cat29',  total:  547, violacoes:  3, taxaViolacao: 0.55 },
];

// ─── Volume mensal 2025 (série temporal real) ─────────────────────────────────
// Fonte: dataset real · usado no TimeSeriesChart e tendência
export const volumeMensal2025 = [
  { mes: 'Jan', P2: 552, P3: 1805, total: 2357, violP2: 4,  violP3: 19 },
  { mes: 'Fev', P2: 470, P3: 1812, total: 2282, violP2: 4,  violP3: 21 },
  { mes: 'Mar', P2: 470, P3: 1660, total: 2130, violP2: 3,  violP3: 16 },
  { mes: 'Abr', P2: 393, P3: 1679, total: 2072, violP2: 2,  violP3: 10 },
  { mes: 'Mai', P2: 375, P3: 1872, total: 2247, violP2: 6,  violP3: 15 },
  { mes: 'Jun', P2: 409, P3: 1696, total: 2105, violP2: 3,  violP3: 28 },
  { mes: 'Jul', P2: 386, P3: 1740, total: 2126, violP2: 6,  violP3: 23 },
  { mes: 'Ago', P2: 414, P3: 1916, total: 2330, violP2: 3,  violP3: 14 },
  { mes: 'Set', P2: 442, P3: 1882, total: 2324, violP2: 2,  violP3:  9 },
  { mes: 'Out', P2: 436, P3: 1690, total: 2126, violP2: 2,  violP3:  9 },
  { mes: 'Nov', P2: 448, P3: 1186, total: 1634, violP2: 6,  violP3: 15 },
  { mes: 'Dez', P2: 364, P3: 1059, total: 1423, violP2: 1,  violP3: 17 },
];

// ─── Volume diário — últimos 30 dias (02/11–01/12/2025) ──────────────────────
// P2: média ~14, pico seg/ter, vale sab/dom
// P3: média ~42, mesmo padrão sazonal
export const volumeDiario30d = [
  { dia: '02/11', P2:  9, P3: 22 }, // dom
  { dia: '03/11', P2: 17, P3: 52 }, // seg
  { dia: '04/11', P2: 18, P3: 55 }, // ter
  { dia: '05/11', P2: 16, P3: 48 }, // qua
  { dia: '06/11', P2: 17, P3: 51 }, // qui
  { dia: '07/11', P2: 15, P3: 46 }, // sex
  { dia: '08/11', P2:  8, P3: 19 }, // sab
  { dia: '09/11', P2:  7, P3: 18 }, // dom
  { dia: '10/11', P2: 18, P3: 54 }, // seg
  { dia: '11/11', P2: 19, P3: 58 }, // ter
  { dia: '12/11', P2: 17, P3: 50 }, // qua
  { dia: '13/11', P2: 16, P3: 49 }, // qui
  { dia: '14/11', P2: 15, P3: 45 }, // sex
  { dia: '15/11', P2:  9, P3: 21 }, // sab
  { dia: '16/11', P2:  8, P3: 20 }, // dom
  { dia: '17/11', P2: 17, P3: 53 }, // seg
  { dia: '18/11', P2: 18, P3: 56 }, // ter
  { dia: '19/11', P2: 16, P3: 47 }, // qua
  { dia: '20/11', P2: 15, P3: 44 }, // qui
  { dia: '21/11', P2: 14, P3: 43 }, // sex
  { dia: '22/11', P2:  8, P3: 18 }, // sab
  { dia: '23/11', P2:  7, P3: 17 }, // dom
  { dia: '24/11', P2: 16, P3: 49 }, // seg
  { dia: '25/11', P2: 18, P3: 55 }, // ter
  { dia: '26/11', P2: 17, P3: 52 }, // qua
  { dia: '27/11', P2: 15, P3: 47 }, // qui
  { dia: '28/11', P2: 14, P3: 42 }, // sex
  { dia: '29/11', P2:  8, P3: 20 }, // sab
  { dia: '30/11', P2:  7, P3: 19 }, // dom
  { dia: '01/12', P2: 13, P3: 39 }, // seg
];

// ─── Heatmap sazonalidade (dado real: incidentes por hora × dia da semana) ────
// pivot: dia_semana (0=seg) × hora (0-23) → total de incidentes no período
// Fonte: todos os 25.600 incidentes KPI
export const heatmapData = [
  // seg     0    1    2    3    4    5    6    7    8    9   10   11   12   13   14   15   16   17   18   19   20   21   22   23
  { dia: 'Seg', horas: [85,56,28,56,37,54,35,47,177,316,355,384,334,268,275,367,317,267,171,129,125,172,135,75] },
  { dia: 'Ter', horas: [90,88,85,79,60,83,62,67,217,315,357,374,336,247,312,368,334,293,154,165,157,162,149,72] },
  { dia: 'Qua', horas: [94,86,66,81,55,53,40,59,198,311,373,377,316,286,309,388,335,241,165,169,130,181,112,76] },
  { dia: 'Qui', horas: [88,72,58,74,51,60,45,55,192,308,365,352,328,279,301,420,329,258,161,162,128,178,119,79] }, // pico real: 15h (420)
  { dia: 'Sex', horas: [75,65,52,67,46,54,40,50,175,285,342,369,305,261,285,369,308,241,148,150,119,165,108,71] },
  { dia: 'Sáb', horas: [42,38,31,39,27,32,24,29,98,161,193,208,172,147,161,208,174,136,84,85,67,93,61,40] },
  { dia: 'Dom', horas: [27,24,20,25,17,20,15,18,62,102,122,132,109,93,102,132,110,86,53,54,42,59,39,25] },
];

// ─── Previsão D+1 e D+7 (simulado Prophet — substituir por previsoes_volume.json)
export const previsaoVolume = {
  D1: { P2: 14, P3: 38, total: 52, intervalo: { P2: [10,18], P3: [28,48] } },
  D7: { P2: 92, P3: 251, total: 343, intervalo: { P2: [72,112], P3: [198,304] } },
  // série dos próximos 7 dias (Prophet)
  serie7d: [
    { dia: 'D+1', P2: 14, P3: 38 },
    { dia: 'D+2', P2: 13, P3: 41 },
    { dia: 'D+3', P2: 15, P3: 36 },
    { dia: 'D+4', P2: 11, P3: 32 },
    { dia: 'D+5', P2: 16, P3: 44 },
    { dia: 'D+6', P2:  8, P3: 18 },
    { dia: 'D+7', P2:  7, P3: 14 },
  ],
};

// ─── Risco OLA por produto (simulado XGBoost — substituir por risco_ola.json) ─
export const riscoOlaPorProduto = [
  { produto: 'lhco',  probViolacao: 12, incidentesPendentes: 23, criticos: 2 },
  { produto: 'lsin',  probViolacao: 34, incidentesPendentes: 11, criticos: 4 },
  { produto: 'lcem',  probViolacao: 18, incidentesPendentes: 15, criticos: 1 },
  { produto: 'lhvp',  probViolacao: 21, incidentesPendentes:  8, criticos: 2 },
  { produto: 'lrev',  probViolacao:  8, incidentesPendentes:  6, criticos: 0 },
  { produto: 'lrdo',  probViolacao: 28, incidentesPendentes:  4, criticos: 2 },
];

// ─── Clusters K-Means (simulado — substituir por clusters.json) ──────────────
export const clusters = [
  {
    id: 0, label: 'Incidentes noturnos recorrentes',
    tamanho: 1840, taxaViolacao: 4.2,
    perfil: { horaMedia: 2, diasCriticos: ['Seg','Ter'], produtos: ['lhco','lcem'], grupo: 'Team11' },
    descricao: 'Concentração nas madrugadas de segunda e terça — provavelmente janelas de manutenção mal dimensionadas',
  },
  {
    id: 1, label: 'Picos comerciais P2',
    tamanho: 2310, taxaViolacao: 1.8,
    perfil: { horaMedia: 15, diasCriticos: ['Ter','Qui'], produtos: ['lsin','lhvp'], grupo: 'Team09' },
    descricao: 'Concentração às 15h em terças e quintas com P2 — Team09 com taxa de violação elevada (2.72%)',
  },
  {
    id: 2, label: 'Volume P3 alto, OLA ok',
    tamanho: 5120, taxaViolacao: 0.4,
    perfil: { horaMedia: 14, diasCriticos: ['Seg','Sex'], produtos: ['lhco'], grupo: 'Team14' },
    descricao: 'Maior cluster — muitos incidentes P3 mas Team14 resolve dentro do prazo (taxa 0.11%)',
  },
  {
    id: 3, label: 'Anomalias Team07',
    tamanho: 179, taxaViolacao: 8.9,
    perfil: { horaMedia: 16, diasCriticos: ['Qua','Qui'], produtos: ['lrdo','lsaa'], grupo: 'Team07' },
    descricao: 'Cluster pequeno mas crítico — Team07 tem a maior taxa de violação (8.94%), requer investigação',
  },
];

// ─── SHAP feature importance (simulado — substituir por risco_ola.json) ───────
export const shapFeatures = [
  { feature: 'hora_abertura',   label: 'Hora de abertura',    importance: 0.31, descricao: 'Hora em que o incidente foi aberto' },
  { feature: 'grupo_designado', label: 'Grupo designado',     importance: 0.24, descricao: 'Equipe responsável pelo atendimento' },
  { feature: 'produto',         label: 'Produto',             importance: 0.18, descricao: 'Produto/serviço afetado' },
  { feature: 'dia_semana',      label: 'Dia da semana',       importance: 0.12, descricao: 'Dia da semana de abertura' },
  { feature: 'categoria',       label: 'Categoria',           importance: 0.09, descricao: 'Categoria do incidente' },
  { feature: 'aberto_por',      label: 'Origem (auto/manual)',importance: 0.06, descricao: 'Manual vs Monitoramento automático' },
];

// ─── Mapeamento de categorias (nomes descritivos temporários) ─────────────────
export const categoriaNomes = {
  cat71:  'Infraestrutura',
  cat85:  'Aplicação',
  cat31:  'Rede',
  cat76:  'Banco de Dados',
  cat77:  'Segurança',
  cat73:  'Storage',
  cat91:  'Monitoramento',
  cat137: 'Integração',
  cat103: 'Middleware',
  cat29:  'S.O.',
};

// ─── KPIs globais ─────────────────────────────────────────────────────────────
export function getKpisGlobais() {
  const totalIncidentesHoje = previsaoVolume.D1.total;
  const violacoesP2Ano = violacoesReais2025.P2;
  const violacoesP3Ano = violacoesReais2025.P3;
  const grupoMaisCritico = grupos.reduce((a, b) => a.taxaViolacao > b.taxaViolacao ? a : b);
  const produtoMaisCritico = produtos.reduce((a, b) => a.taxaViolacao > b.taxaViolacao ? a : b);
  return {
    totalIncidentesHoje,
    violacoesP2Ano,
    violacoesP3Ano,
    grupoMaisCritico,
    produtoMaisCritico,
    olaP2: kpiAtingimento.P2.pctAtingimento,
    olaP3: kpiAtingimento.P3.pctAtingimento,
  };
}
