"""
plot_model_evolution.py
Evolução percentual de MAE entre versões do Prophet vs baseline v1.
Saída: outputs/model_evolution.png
"""

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── Dados ─────────────────────────────────────────────────────────────────────
MAE = {
    'v1 — padrão':          [17.94, 14.70, 11.94, 22.82, 20.43, 27.59, 24.38],
    'v2 — +lag_1d':         [17.21, 10.88, 11.25, 19.26, 18.03, 20.01, 22.58],
    'v3 — Fourier+aditivo': [22.42, 20.33, 17.41, 20.62, 31.26, 39.95, 24.62],
    'v4 — dias úteis/FDS':  [26.14, 17.12, 20.63, 32.19, 30.54, 46.71, 40.60],
    'v5 — todos os lags':   [19.26, 10.08,  8.25, 15.75,  9.66, 22.59, 18.51],
    'ensemble':             [17.42, 10.08,  8.25, 12.31,  9.66, 20.84, 13.66],
}
HORIZONS = ['D+1', 'D+2', 'D+3', 'D+4', 'D+5', 'D+6', 'D+7']
BASELINE = 'v1 — padrão'

CORES = {
    'v2 — +lag_1d':         '#4EA8E8',
    'v3 — Fourier+aditivo': '#E85D5D',
    'v4 — dias úteis/FDS':  '#E8A030',
    'v5 — todos os lags':   '#3DBA8A',
    'ensemble':             '#A89EF5',
}
ESTILOS = {
    'v2 — +lag_1d':         ('o',  '-',  1.8),
    'v3 — Fourier+aditivo': ('s',  '--', 1.6),
    'v4 — dias úteis/FDS':  ('^',  '--', 1.6),
    'v5 — todos os lags':   ('D',  '-',  1.8),
    'ensemble':             ('*',  '-',  2.6),
}

# ── Calcular % de variação vs baseline ────────────────────────────────────────
baseline = np.array(MAE[BASELINE])
evolucao = {
    nome: ((np.array(vals) - baseline) / baseline * 100)
    for nome, vals in MAE.items()
    if nome != BASELINE
}

# ── Figura ────────────────────────────────────────────────────────────────────
BG   = '#0d0d0d'
BG2  = '#161616'
GRID = '#242424'

fig, (ax_main, ax_table) = plt.subplots(
    2, 1, figsize=(15, 10),
    gridspec_kw={'height_ratios': [3, 1]},
    facecolor=BG
)
fig.subplots_adjust(hspace=0.08)

# ── Painel principal ──────────────────────────────────────────────────────────
ax_main.set_facecolor(BG)
x = np.arange(len(HORIZONS))

# Faixas de fundo
ax_main.axhspan(-80,  0,  alpha=0.06, color='#3DBA8A', zorder=1)
ax_main.axhspan(  0, 100, alpha=0.06, color='#E85D5D', zorder=1)

# Linha de referência v1
ax_main.axhline(0, color='#555555', linewidth=1.4,
                linestyle='--', zorder=2, label='v1 — padrão (baseline = 0%)')

# Grade
ax_main.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
ax_main.set_axisbelow(True)

# Linhas dos modelos
for nome, pct in evolucao.items():
    marc, ls, lw = ESTILOS[nome]
    cor = CORES[nome]
    ms  = 12 if nome == 'ensemble' else 9
    zo  =  6 if nome == 'ensemble' else 4
    alpha = 1.0 if nome == 'ensemble' else 0.88

    ax_main.plot(x, pct, color=cor, linewidth=lw, linestyle=ls,
                 marker=marc, markersize=ms, label=nome,
                 zorder=zo, alpha=alpha, solid_capstyle='round')

    # Anotações somente nos extremos relevantes
    for i, v in enumerate(pct):
        if abs(v) < 8:
            continue
        # Posição: acima se piora, abaixo se melhora
        offset_y = 14 if v > 0 else -16
        ax_main.annotate(
            f'{v:+.0f}%',
            xy=(x[i], v),
            xytext=(0, offset_y),
            textcoords='offset points',
            ha='center', va='center',
            fontsize=10, fontweight='bold',
            color=cor,
            bbox=dict(boxstyle='round,pad=0.25', fc=BG, ec=cor, lw=0.8, alpha=0.85),
        )

# Rótulos de zona
ax_main.text(0.01, 0.10, '▼  melhora vs baseline',
             transform=ax_main.transAxes, fontsize=11,
             color='#3DBA8A', alpha=0.7, va='bottom')
ax_main.text(0.01, 0.92, '▲  piora vs baseline',
             transform=ax_main.transAxes, fontsize=11,
             color='#E85D5D', alpha=0.7, va='top')

# Eixos
ax_main.set_xticks(x)
ax_main.set_xticklabels(HORIZONS, fontsize=14, color='#cccccc', fontweight='bold')
ax_main.tick_params(axis='x', length=0, pad=8)
ax_main.tick_params(axis='y', colors='#666666', labelsize=12)
ax_main.set_ylabel('Variação de MAE vs v1 (%)', fontsize=13, color='#aaaaaa', labelpad=12)
ax_main.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:+.0f}%'))

for spine in ax_main.spines.values():
    spine.set_edgecolor('#2a2a2a')

ax_main.set_xlim(-0.4, 6.4)
ax_main.set_ylim(-85, 110)

# Título
ax_main.set_title(
    'Evolução do MAE por versão do modelo Prophet\n'
    'Predictfy × Locaweb · FIAP Challenge 2026',
    fontsize=15, color='#eeeeee', pad=18, loc='left', fontweight='normal'
)

# Legenda
leg = ax_main.legend(
    loc='upper left', fontsize=11,
    framealpha=0.25, edgecolor='#333333',
    labelcolor='#cccccc', facecolor='#111111',
    borderpad=0.9, handlelength=2.2, handleheight=1.2,
    labelspacing=0.6,
)
for line in leg.get_lines():
    line.set_linewidth(2.5)

# ── Painel de tabela de MAE absoluto ─────────────────────────────────────────
ax_table.set_facecolor(BG2)
ax_table.set_xlim(-0.5, 6.5)
ax_table.set_ylim(-0.5, len(MAE) - 0.5)
ax_table.axis('off')

modelos_ord = [BASELINE,
               'v2 — +lag_1d', 'v3 — Fourier+aditivo',
               'v4 — dias úteis/FDS', 'v5 — todos os lags', 'ensemble']

# Cabeçalho
ax_table.text(-0.45, len(MAE) - 0.5, 'MAE absoluto',
              fontsize=11, color='#888888', va='top', style='italic')
for j, h in enumerate(HORIZONS):
    ax_table.text(j, len(MAE) - 0.55, h,
                  fontsize=11, color='#888888',
                  ha='center', va='top', fontweight='bold')

# Linhas da tabela
for i, nome in enumerate(reversed(modelos_ord)):
    row_y = i
    cor_nome = CORES.get(nome, '#888888')

    # Nome do modelo
    ax_table.text(-0.45, row_y, nome, fontsize=10,
                  color=cor_nome if nome != BASELINE else '#666666',
                  va='center', fontweight='bold' if nome == 'ensemble' else 'normal')

    # Valores de MAE
    vals = MAE[nome]
    min_val = min(vals)
    for j, v in enumerate(vals):
        destaque = (v == min_val)
        cor_val = '#ffffff' if destaque else '#aaaaaa'
        fw = 'bold' if destaque else 'normal'
        ax_table.text(j, row_y, f'{v:.1f}',
                      fontsize=10, ha='center', va='center',
                      color=cor_val, fontweight=fw)
        if destaque:
            ax_table.add_patch(plt.Rectangle(
                (j - 0.42, row_y - 0.38), 0.84, 0.76,
                fc='#1d3d2a', ec='#3DBA8A', lw=0.8,
                zorder=0, transform=ax_table.transData, clip_on=False
            ))

# Separador entre os dois painéis
fig.add_artist(plt.Line2D([0.08, 0.92], [0.315, 0.315],
                           transform=fig.transFigure,
                           color='#2a2a2a', linewidth=0.8))

# ── Salvar ────────────────────────────────────────────────────────────────────
OUT = '/Users/pedro/Documents/Estudos/fiap/locaweb/outputs/model_evolution.png'
plt.savefig(OUT, dpi=180, bbox_inches='tight', facecolor=BG)
plt.close()
print(f'✅ Salvo: {OUT}')
