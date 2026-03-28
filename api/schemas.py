"""
schemas.py — Pydantic response models da API Predictfy.

Glossário:
  P2: Incidentes de prioridade Alta — OLA ≤ 4h
  P3: Incidentes de prioridade Média — OLA ≤ 12h
  OLA: Acordo de Nível Operacional — prazo contratual de resolução
  D+N: Horizonte de previsão (D+1 = amanhã, D+7 = 7 dias à frente)
  ensemble: combinação dos modelos Prophet v5 + v6, selecionando o melhor por horizonte
"""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ────────────────────────────────────────────────────────────────────────────────
# Genérico
# ────────────────────────────────────────────────────────────────────────────────

class NaoDisponivel(BaseModel):
    """Retornado quando o arquivo de modelo ainda não foi gerado em outputs/."""
    disponivel: Literal[False] = Field(False, example=False)
    mensagem: str = Field(..., example="Modelo Prophet ainda não treinado")


class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    timestamp: str = Field(..., example="2026-03-26T12:00:00+00:00")
    modelos_disponiveis: list[str] = Field(
        ...,
        example=["previsoes_volume"],
        description="Arquivos presentes em outputs/ sem a extensão .json",
    )


# ────────────────────────────────────────────────────────────────────────────────
# Previsões Prophet
# ────────────────────────────────────────────────────────────────────────────────

class PrevisaoHorizonte(BaseModel):
    """Previsão pontual para um horizonte (D+1 ou D+7)."""
    yhat: float = Field(..., example=37.2, description="Valor previsto pelo ensemble")
    lower: float = Field(..., example=21.5, description="Limite inferior do intervalo de confiança")
    upper: float = Field(..., example=53.1, description="Limite superior do intervalo de confiança")
    modelo_usado: str = Field(..., example="v6", description="Modelo que teve menor MAE neste horizonte (v5 ou v6)")


class PrevisaoSerieDia(BaseModel):
    """Um ponto da série temporal gerada pelo Prophet (D+1 a D+7)."""
    dia: str = Field(..., example="01/01", description="Data formatada DD/MM para exibição")
    ds: str = Field(..., example="2026-01-01", description="Data ISO 8601")
    horizonte: str = Field(..., example="D+1", description="Horizonte de previsão")
    modelo: str = Field(..., example="v6", description="Modelo Prophet selecionado para este dia")
    mae_usado: float = Field(..., example=7.75, description="MAE do modelo neste horizonte (cross-validation)")
    yhat: float = Field(..., example=37.2, description="Volume previsto de incidentes")
    yhat_lower: float = Field(..., example=21.5)
    yhat_upper: float = Field(..., example=53.1)


class PrevisaoMetricas(BaseModel):
    """Métricas de erro do modelo Prophet (cross-validation com janela de 180 dias)."""
    mae_d1: float = Field(..., example=17.4, description="MAE no horizonte D+1")
    mae_d7: float = Field(..., example=14.2, description="MAE no horizonte D+7")
    nota: str = Field(..., example="ensemble v5+v6 — melhor modelo por horizonte")


class PrevisaoModeloDetalhe(BaseModel):
    """Saída completa do Prophet ensemble para uma série (total, P2 ou P3)."""
    modelo: str = Field(..., example="prophet_ensemble_total")
    gerado_em: str = Field(..., example="2026-03-14")
    abordagem: str = Field(..., example="ensemble v5+v6 — melhor modelo por horizonte")
    D1: PrevisaoHorizonte
    D7: PrevisaoHorizonte
    serie_7d: list[PrevisaoSerieDia]
    metricas: PrevisaoMetricas


class PrevisaoCompletaResponse(BaseModel):
    """
    Resposta completa de /previsoes — inclui todas as séries e metadados do modelo.
    Útil para integração avançada ou debug do modelo.
    """
    disponivel: bool = Field(True, example=True)
    total: PrevisaoModeloDetalhe = Field(..., description="Série total (P2 + P3)")
    p2: PrevisaoModeloDetalhe = Field(..., description="Série P2 — prioridade alta (OLA 4h)")
    p3: PrevisaoModeloDetalhe = Field(..., description="Série P3 — prioridade média (OLA 12h)")


class PrevisaoD1Response(BaseModel):
    """Resumo do D+1 para KPI cards do dashboard."""
    disponivel: bool = Field(True, example=True)
    total: int = Field(..., example=69, description="Total de incidentes previstos para amanhã")
    p2: Optional[int] = Field(None, example=15, description="Incidentes P2 previstos — None quando LSTM (só total)")
    p3: Optional[int] = Field(None, example=54, description="Incidentes P3 previstos — None quando LSTM (só total)")
    modelo_usado: str = Field(..., example="lstm_v2", description="Modelo ativo: lstm_v2 | prophet_mc_ensemble | prophet_original")
    mae: Optional[float] = Field(None, example=13.15, description="MAE holdout do modelo (disponível apenas para LSTM)")


class PrevisaoD7Response(BaseModel):
    """Resumo do D+7 para KPI cards do dashboard."""
    disponivel: bool = Field(True, example=True)
    total: int = Field(..., example=65, description="Total de incidentes previstos em 7 dias")
    p2: Optional[int] = Field(None, example=15, description="Incidentes P2 previstos — None quando LSTM (só total)")
    p3: Optional[int] = Field(None, example=50, description="Incidentes P3 previstos — None quando LSTM (só total)")
    modelo_usado: str = Field(..., example="lstm_v2", description="Modelo ativo: lstm_v2 | prophet_mc_ensemble | prophet_original")
    mae: Optional[float] = Field(None, example=13.15, description="MAE holdout do modelo (disponível apenas para LSTM)")


class PrevisaoDia(BaseModel):
    """Um ponto da série formatada para o gráfico de área do dashboard."""
    dia: str = Field(..., example="01/01", description="Label do eixo X no formato DD/MM")
    ds: str = Field(..., example="2026-01-01", description="Data ISO 8601")
    total: int = Field(..., example=69, description="Volume total previsto")
    P2: Optional[int] = Field(None, example=15, description="Incidentes P2 previstos — None quando LSTM")
    P3: Optional[int] = Field(None, example=54, description="Incidentes P3 previstos — None quando LSTM")


class PrevisaoSerieResponse(BaseModel):
    """Série D+1 a D+7 formatada para o gráfico de área do MonitoramentoPage."""
    disponivel: bool = Field(True, example=True)
    modelo_usado: str = Field(..., example="lstm_v2")
    serie: list[PrevisaoDia]


class ModelosDisponiveisResponse(BaseModel):
    """Status de disponibilidade dos modelos de previsão e hierarquia ativa."""
    lstm: bool = Field(..., description="previsoes_lstm.json presente em outputs/")
    prophet_mc: bool = Field(..., description="previsoes_volume_mc.json presente em outputs/")
    prophet_original: bool = Field(..., description="previsoes_volume.json presente em outputs/")
    modelo_ativo: str = Field(..., example="lstm_v2", description="Modelo sendo usado pelos endpoints /previsoes/*")
    mae_modelo_ativo: Optional[float] = Field(None, example=13.15, description="MAE holdout do modelo ativo (só LSTM tem)")


# ────────────────────────────────────────────────────────────────────────────────
# Histórico ITSM
# ────────────────────────────────────────────────────────────────────────────────

class HistoricoMensalItem(BaseModel):
    """Volume mensal de incidentes KPI com contagem de violações de OLA."""
    mes: str = Field(..., example="Jan", description="Mês abreviado em português")
    P2: int = Field(..., example=552, description="Total de incidentes P2 no mês")
    P3: int = Field(..., example=1805, description="Total de incidentes P3 no mês")
    total: int = Field(..., example=2357, description="P2 + P3")
    violP2: int = Field(..., example=4, description="Violações de OLA P2 no mês (> 4h)")
    violP3: int = Field(..., example=19, description="Violações de OLA P3 no mês (> 12h)")


class HistoricoDiarioItem(BaseModel):
    """Volume diário de incidentes KPI — 30 dias de dezembro/2025."""
    dia: str = Field(..., example="02/12", description="Data no formato DD/MM")
    P2: int = Field(..., example=17, description="Incidentes P2 abertos no dia")
    P3: int = Field(..., example=62, description="Incidentes P3 abertos no dia")


class HeatmapItem(BaseModel):
    """Linha do heatmap de sazonalidade — um dia da semana com 24 valores horários."""
    dia: str = Field(..., example="Seg", description="Dia da semana abreviado em português")
    horas: list[int] = Field(
        ...,
        min_length=24,
        max_length=24,
        example=[85, 56, 28, 56, 37, 54, 35, 47, 177, 316, 355, 384,
                 334, 268, 275, 367, 317, 267, 171, 129, 125, 172, 135, 75],
        description="24 contagens — índice 0 = hora 00h, índice 23 = hora 23h",
    )


# ────────────────────────────────────────────────────────────────────────────────
# Risco OLA — XGBoost (notebook 04 — pendente)
# ────────────────────────────────────────────────────────────────────────────────

class RiscoProdutoItem(BaseModel):
    """Risco de violação de OLA por produto com incidentes em aberto."""
    produto: str = Field(..., example="lhco", description="Código interno do produto Locaweb")
    probViolacao: float = Field(..., example=42.0, description="Probabilidade de violar OLA (%) — XGBoost score")
    incidentesPendentes: int = Field(..., example=23, description="Incidentes em aberto no produto")
    criticos: Optional[int] = Field(None, example=2, description="Incidentes com risco > 50%")


class RiscoGrupoItem(BaseModel):
    """Taxa histórica de violação de OLA por grupo de atendimento."""
    grupo: str = Field(..., example="Team07", description="Grupo de atendimento ITSM")
    taxaViolacao: float = Field(..., example=8.94, description="% de incidentes que violaram OLA (histórico 2025)")


class RiscoProdutosResponse(BaseModel):
    """Lista de produtos com risco de violação, ordenada decrescente por probabilidade."""
    disponivel: bool = Field(True, example=True)
    produtos: list[RiscoProdutoItem]


class RiscoGruposResponse(BaseModel):
    """Lista de grupos com taxa de violação histórica, ordenada decrescente."""
    disponivel: bool = Field(True, example=True)
    grupos: list[RiscoGrupoItem]


# ────────────────────────────────────────────────────────────────────────────────
# KPI Operacional (notebook 07 — pendente)
# ────────────────────────────────────────────────────────────────────────────────

class KpiPrioridade(BaseModel):
    """KPI de atingimento de OLA por prioridade — calculado via SPC (média + 1σ)."""
    violacoesAno:    int   = Field(..., example=42,  description="Total de violações no período")
    metaAnual:       int   = Field(..., example=63,  description="Meta derivada via SPC (média + 1σ × meses)")
    metaMensal:      float = Field(..., example=5.2, description="Meta mensal (média + 1σ)")
    pctUtilizado:    float = Field(..., example=66.7, description="% da cota utilizada (real/meta × 100)")
    margemRestante:  int   = Field(..., example=21,  description="Violações restantes antes de atingir a meta")
    tendencia:       str   = Field(..., example="dentro_da_meta")
    olaHoras:        int   = Field(..., example=4)
    pctAtingimento:  int   = Field(..., example=100, description="Para o gauge: 100 = dentro da meta, <100 = acima")
    mesesAnomalos:   list[str] = Field(default=[], example=["Mai", "Jul", "Nov"])
    periodo_filtro:  Optional[str] = Field(None, example="ano")


class KpiResponse(BaseModel):
    """KPI de atingimento das metas de OLA — P2 e P3 via metodologia SPC."""
    disponivel:     bool            = Field(True,  example=True)
    metodologia:    Optional[str]   = Field(None,  example="SPC — meta derivada da distribuição histórica")
    gerado_em:      Optional[str]   = Field(None,  example="2026-03-28")
    periodo_filtro: Optional[str]   = Field(None,  example="ano")
    P2:             KpiPrioridade   = Field(...,   description="P2 — meta SPC 63 violações/ano")
    P3:             KpiPrioridade   = Field(...,   description="P3 — meta SPC 280 violações/ano")
    por_mes:        Optional[dict]  = Field(None,  description="Violações mensais por prioridade")


# ────────────────────────────────────────────────────────────────────────────────
# Context — snapshot para o chatbot Gemini
# ────────────────────────────────────────────────────────────────────────────────

class ContextD1D7(BaseModel):
    total: int = Field(..., example=69)
    p2: Optional[int] = Field(None, example=15, description="None quando LSTM (só prevê total)")
    p3: Optional[int] = Field(None, example=54, description="None quando LSTM (só prevê total)")


class ContextPrevisoes(BaseModel):
    disponivel: bool
    modelo_ativo: Optional[str] = Field(None, example="lstm_v2")
    mae_92_dias: Optional[float] = Field(None, example=13.15)
    D1: Optional[ContextD1D7] = None
    D7: Optional[ContextD1D7] = None


class ContextRisco(BaseModel):
    disponivel: bool
    top_produtos: Optional[list[dict]] = Field(None, description="Top 3 produtos por probabilidade de violação")
    top_grupos: Optional[list[dict]] = Field(None, description="Top 3 grupos por taxa de violação")


class ContextClusters(BaseModel):
    disponivel: bool
    resumo: Optional[dict] = Field(None, description="Resumo dos clusters K-Means")


class ContextKpi(BaseModel):
    disponivel: bool
    P2: Optional[dict] = None
    P3: Optional[dict] = None


class OperacionalInfo(BaseModel):
    """Metadados operacionais fixos do contrato de nível de serviço."""
    ola_targets: dict = Field(..., example={"P2": "4h", "P3": "12h"})
    metas_anuais: dict = Field(..., example={"P2": "36-39", "P3": "231-263"})
    violacoes_2025: dict = Field(..., example={"P2": 42, "P3": 196})


class ContextResponse(BaseModel):
    """
    Snapshot operacional completo — projetado para uso como contexto do chatbot Gemini.
    Agrega todos os modelos disponíveis em uma única chamada.
    """
    timestamp: str = Field(..., example="2026-03-26T12:00:00+00:00")
    previsoes: ContextPrevisoes
    risco: ContextRisco
    clusters: ContextClusters
    kpi: ContextKpi
    operacional: OperacionalInfo


# ────────────────────────────────────────────────────────────────────────────────
# Clusters K-Means (notebook 05 — pendente)
# ────────────────────────────────────────────────────────────────────────────────

class ClustersResponse(BaseModel):
    """Segmentação K-Means de padrões de incidentes — disponível após notebook 05."""
    disponivel: bool = Field(True, example=True)
