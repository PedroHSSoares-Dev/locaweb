"""
K-Means — segmentação de padrões de incidentes ITSM.

Avalia K de 2 a 10 com 3 métricas (Silhouette, Calinski-Harabasz, Davies-Bouldin),
seleciona K ímpar >= K_MIN por voto majoritário e exporta outputs/clusters.json.
"""
from __future__ import annotations

import json
import warnings
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).parents[2]
PARQUET_PATH = PROJECT_ROOT / "data" / "processed" / "incidents_features.parquet"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "clusters.json"

CLUSTER_FEATURES = [
    "hora", "dia_semana", "mes", "periodo_dia",
    "is_horario_comercial", "is_fim_de_semana", "prioridade_bin",
    "lag_1d", "rolling_7d",
    "produto_freq", "grupo_freq",
]
TARGET = "target_ola"

K_MIN = 5
K_MAX_UTIL = 9
K_RANGE = range(2, 11)


def load_data(path: Path = PARQUET_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} não encontrado.\nExecute: python src/data/preprocessor.py"
        )
    df = pd.read_parquet(path)

    missing = [f for f in CLUSTER_FEATURES if f not in df.columns]
    if missing:
        raise ValueError(f"Features faltando: {missing}\nExecute: python src/data/preprocessor.py")

    df_cl = df[CLUSTER_FEATURES + [TARGET]].copy()
    df_cl[["lag_1d", "rolling_7d"]] = df_cl[["lag_1d", "rolling_7d"]].fillna(0)
    assert df_cl.isnull().sum().sum() == 0, "Dataset com nulos"
    return df_cl


def find_best_k(X_scaled: np.ndarray) -> tuple[int, dict]:
    """Avalia K de 2 a 10 e retorna o K ideal (ímpar, >= K_MIN)."""
    n_sample = min(10_000, len(X_scaled))
    idx_sample = np.random.choice(len(X_scaled), n_sample, replace=False)
    X_sample = X_scaled[idx_sample]

    inertias, sil_scores, ch_scores, db_scores = [], [], [], []

    print(f"Avaliando K de 2 a 10 (candidatos ímpares >= {K_MIN})...")
    for k in K_RANGE:
        km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
        lbl = km.fit_predict(X_scaled)
        lbl_sample = lbl[idx_sample]

        inertias.append(km.inertia_)
        sil_scores.append(silhouette_score(X_sample, lbl_sample, sample_size=min(5000, n_sample)))
        ch_scores.append(calinski_harabasz_score(X_scaled, lbl))
        db_scores.append(davies_bouldin_score(X_scaled, lbl))

    valid = [
        (k, s, c, d)
        for k, s, c, d in zip(K_RANGE, sil_scores, ch_scores, db_scores)
        if K_MIN <= k <= K_MAX_UTIL and k % 2 == 1
    ]

    if not valid:
        raise ValueError(f"Nenhum K ímpar válido em [{K_MIN}, {K_MAX_UTIL}]")

    best_k_sil = max(valid, key=lambda x: x[1])[0]
    best_k_ch = max(valid, key=lambda x: x[2])[0]
    best_k_db = min(valid, key=lambda x: x[3])[0]

    votos = [best_k_sil, best_k_ch, best_k_db]
    k_vencedor = Counter(votos).most_common(1)[0][0]
    if Counter(votos).most_common(1)[0][1] == 1:
        k_vencedor = best_k_sil  # desempate: Silhouette

    print(f"K selecionado (voto majoritário): {k_vencedor}")

    metricas_k = {
        k: {"inertia": inertias[i], "silhouette": sil_scores[i],
            "calinski_harabasz": ch_scores[i], "davies_bouldin": db_scores[i]}
        for i, k in enumerate(K_RANGE)
    }
    return k_vencedor, metricas_k


def train(df: pd.DataFrame) -> dict:
    """Normaliza, seleciona K, treina K-Means e retorna resultados."""
    X_raw = df[CLUSTER_FEATURES].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    np.random.seed(42)
    k_final, metricas_k = find_best_k(X_scaled)

    print(f"Treinando K-Means com K={k_final}...")
    kmeans = KMeans(n_clusters=k_final, random_state=42, n_init=20, max_iter=500)
    labels = kmeans.fit_predict(X_scaled)

    df_cl = df.copy()
    df_cl["cluster"] = labels

    inertia_final = kmeans.inertia_
    sil_final = silhouette_score(X_scaled, labels, sample_size=min(10_000, len(X_scaled)))
    ch_final = calinski_harabasz_score(X_scaled, labels)
    db_final = davies_bouldin_score(X_scaled, labels)

    print(f"Silhouette={sil_final:.4f} | CH={ch_final:.1f} | DB={db_final:.4f}")

    # Perfil dos clusters
    periodo_map = {0: "madrugada", 1: "manhã", 2: "tarde", 3: "noite"}
    cluster_info = []

    for c in sorted(df_cl["cluster"].unique()):
        sub = df_cl[df_cl["cluster"] == c]
        n = len(sub)
        viol = int(sub[TARGET].sum())
        taxa = viol / n * 100

        hora_med = sub["hora"].mean()
        pct_p2 = sub["prioridade_bin"].mean() * 100
        pct_comerc = sub["is_horario_comercial"].mean() * 100
        pct_fds = sub["is_fim_de_semana"].mean() * 100
        periodo_m = periodo_map[int(sub["periodo_dia"].mode()[0])]

        perfil_medio = df_cl[df_cl["cluster"] == c][CLUSTER_FEATURES].mean()
        taxa_media_geral = df_cl[TARGET].mean() * 100

        if pct_p2 > 40:
            nome = "Alta Prioridade P2-dominante"
        elif pct_fds > 30:
            nome = "Fim de Semana / Noturno"
        elif hora_med < 8 or hora_med > 18:
            nome = "Fora do Horário Comercial"
        elif taxa > taxa_media_geral * 1.3:
            nome = f"Risco Elevado — {periodo_m.capitalize()}"
        else:
            nome = f"Operação Normal — {periodo_m.capitalize()}"

        cluster_info.append({
            "id": int(c),
            "nome": nome,
            "tamanho": n,
            "pct_total": round(n / len(df_cl) * 100, 2),
            "taxa_violacao_pct": round(taxa, 3),
            "total_violacoes": viol,
            "perfil": {
                "hora_media": round(hora_med, 1),
                "dia_semana_medio": round(float(sub["dia_semana"].mean()), 1),
                "prioridade_p2_pct": round(pct_p2, 1),
                "horario_comercial_pct": round(pct_comerc, 1),
                "fim_de_semana_pct": round(pct_fds, 1),
                "periodo_dia_predominante": periodo_m,
            },
        })

    # PCA 2D para visualização
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)

    return {
        "k_final": k_final,
        "kmeans": kmeans,
        "scaler": scaler,
        "labels": labels,
        "df_cl": df_cl,
        "X_scaled": X_scaled,
        "X_pca": X_pca,
        "pca": pca,
        "cluster_info": cluster_info,
        "metricas_finais": {
            "inertia": round(float(inertia_final), 2),
            "silhouette_score": round(float(sil_final), 4),
            "calinski_harabasz": round(float(ch_final), 2),
            "davies_bouldin": round(float(db_final), 4),
            "features_usadas": len(CLUSTER_FEATURES),
            "total_incidentes": int(len(df_cl)),
            "pca_variancia_2d": round(float(pca.explained_variance_ratio_.sum()), 4),
        },
        "metricas_k": metricas_k,
    }


def export_json(results: dict, path: Path = OUTPUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "modelo": "kmeans_segmentacao",
        "gerado_em": date.today().strftime("%Y-%m-%d"),
        "versao": "v2",
        "k": results["k_final"],
        "k_min_utilizado": K_MIN,
        "metricas": results["metricas_finais"],
        "features_clustering": CLUSTER_FEATURES,
        "clusters": results["cluster_info"],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"JSON exportado: {path}")


if __name__ == "__main__":
    print("Carregando features...")
    df = load_data()
    print(f"Dataset: {df.shape}")

    print("\nTreinando K-Means...")
    results = train(df)

    print("\nExportando JSON...")
    export_json(results)
    print("Concluído.")
