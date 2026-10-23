"""Etapa 3 del pipeline: exploración de datos para el reporte de la Entrega 1.

Genera en reports/eda/ las tablas y figuras que van al documento:
  - resumen_variables.csv: tipo, % faltante y estadísticos por variable.
  - desenlaces.csv y metricas_eda.json: frecuencia de cada desenlace.
  - ingresos_por_periodo.csv: ingresos y eventos por semestre.
  - fig1_faltantes.png, fig2_estancia.png, fig3_desenlaces_periodo.png,
    fig4_variables_por_mortalidad.png, fig5_correlaciones.png

Uso:  python src/exploracion.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import yaml

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "reports" / "eda"

DESENLACES = {
    "mortality": "Muerte en UCI",
    "death_30d": "Muerte a 30 días",
    "estancia_prolongada": "Estancia ≥ 7 días",
    "muerte_o_estancia_prolongada": "Muerte o estancia ≥ 7 días",
}
NO_PREDICTORES = ["record_id", "fecha_ingreso", "dias_estancia", "particion_temporal",
                  "mort_esperada_saps3", "mort_esperada_apache", *DESENLACES]
CONTINUAS_CLAVE = ["age", "sofa", "sapsiii", "apacheii", "lactate", "pafi", "creatinine", "platelet"]

plt.rcParams.update({"figure.dpi": 150, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 9})


def resumen_variables(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for col in [c for c in df.columns if c not in NO_PREDICTORES]:
        s = df[col]
        num = pd.to_numeric(s, errors="coerce")
        n_unicos = s.nunique(dropna=True)
        tipo = "categórica" if n_unicos <= 6 else "continua"
        fila = {"variable": col, "tipo": tipo, "n_valores_unicos": n_unicos,
                "pct_faltante": round(s.isna().mean() * 100, 1)}
        if tipo == "continua":
            fila.update({"media": round(num.mean(), 2), "de": round(num.std(), 2),
                         "mediana": round(num.median(), 2), "p25": round(num.quantile(.25), 2),
                         "p75": round(num.quantile(.75), 2), "min": num.min(), "max": num.max()})
        else:
            fila["categorias"] = "; ".join(f"{k}: {v}" for k, v in s.value_counts().sort_index().items())
        filas.append(fila)
    return pd.DataFrame(filas).sort_values("pct_faltante", ascending=False)


def fig_faltantes(res: pd.DataFrame) -> None:
    datos = res[res["pct_faltante"] > 0].sort_values("pct_faltante")
    fig, ax = plt.subplots(figsize=(6, 0.18 * len(datos) + 1))
    colores = np.where(datos["pct_faltante"] > 30, "#c0392b", "#7f8c8d")
    ax.barh(datos["variable"], datos["pct_faltante"], color=colores)
    ax.axvline(30, ls="--", lw=0.8, color="black")
    ax.set_xlabel("% de pacientes sin dato")
    ax.set_title("Datos faltantes por variable (rojo: > 30 %)")
    fig.tight_layout()
    fig.savefig(SALIDA / "fig1_faltantes.png")
    plt.close(fig)


def fig_estancia(df: pd.DataFrame, umbral: int) -> None:
    fig, ax = plt.subplots(figsize=(6, 3))
    dias = df["dias_estancia"].dropna().clip(upper=30)
    ax.hist(dias, bins=range(0, 32), color="#2c7fb8", edgecolor="white")
    ax.axvline(umbral, color="#c0392b", ls="--")
    ax.text(umbral + 0.4, ax.get_ylim()[1] * 0.85, f"≥ {umbral} días: {(df['dias_estancia'] >= umbral).mean():.1%}",
            color="#c0392b")
    ax.set_xlabel("Días de estancia en UCI (truncado en 30)")
    ax.set_ylabel("Pacientes")
    ax.set_title(f"Estancia en UCI: mediana {df['dias_estancia'].median():.0f} días, "
                 f"p90 {df['dias_estancia'].quantile(.9):.0f}")
    fig.tight_layout()
    fig.savefig(SALIDA / "fig2_estancia.png")
    plt.close(fig)


def tabla_periodos(df: pd.DataFrame) -> pd.DataFrame:
    f = df["fecha_ingreso"]
    df = df.assign(semestre=f.dt.year.astype(str) + "-S" + np.where(f.dt.month <= 6, "1", "2"))
    return df.groupby("semestre").agg(
        ingresos=("record_id", "count"),
        muerte_uci=("mortality", "mean"),
        estancia_prolongada=("estancia_prolongada", "mean"),
        estancia_mediana=("dias_estancia", "median"),
        saps3_mediana=("sapsiii", "median"),
    ).round(3).reset_index()


def fig_periodos(per: pd.DataFrame, fecha_corte: str) -> None:
    per = per[per["ingresos"] >= 10]  # se omiten semestres con muy pocos ingresos
    fig, ax1 = plt.subplots(figsize=(6.5, 3))
    ax1.bar(per["semestre"], per["ingresos"], color="#d9d9d9")
    ax1.set_ylabel("Ingresos")
    ax2 = ax1.twinx()
    ax2.plot(per["semestre"], per["muerte_uci"] * 100, "o-", color="#c0392b", label="Muerte en UCI")
    ax2.plot(per["semestre"], per["estancia_prolongada"] * 100, "s-", color="#2c7fb8", label="Estancia ≥ 7 d")
    ax2.set_ylabel("% de pacientes")
    ax2.legend(loc="upper left", frameon=False)
    ax1.set_title(f"Ingresos y desenlaces por semestre (corte temporal: {fecha_corte})")
    fig.tight_layout()
    fig.savefig(SALIDA / "fig3_desenlaces_periodo.png")
    plt.close(fig)


def fig_variables_por_mortalidad(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(9, 4.5))
    etiquetas = df["mortality"].map({0: "Vivo", 1: "Muerto"})
    for ax, var in zip(axes.flat, CONTINUAS_CLAVE):
        sns.boxplot(x=etiquetas, y=pd.to_numeric(df[var], errors="coerce"), ax=ax, hue=etiquetas,
                    order=["Vivo", "Muerto"], palette={"Vivo": "#9ecae1", "Muerto": "#c0392b"},
                    legend=False, fliersize=1.5)
        ax.set_ylim(top=pd.to_numeric(df[var], errors="coerce").quantile(0.99) * 1.1)
        ax.set_title(var)
        ax.set_xlabel("")
        ax.set_ylabel("")
    fig.suptitle("Variables continuas al ingreso según muerte en UCI (eje truncado en el percentil 99)")
    fig.tight_layout()
    fig.savefig(SALIDA / "fig4_variables_por_mortalidad.png")
    plt.close(fig)


def fig_correlaciones(df: pd.DataFrame) -> None:
    cols = [c for c in df.columns if c not in NO_PREDICTORES] + ["mortality", "estancia_prolongada"]
    corr = df[cols].apply(pd.to_numeric, errors="coerce").corr(method="spearman")
    fig, ax = plt.subplots(figsize=(10, 8.5))
    sns.heatmap(corr, cmap="RdBu_r", center=0, vmin=-1, vmax=1, square=True,
                cbar_kws={"shrink": 0.6, "label": "Spearman ρ"}, ax=ax)
    ax.set_title("Correlación de Spearman entre predictores y desenlaces")
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(SALIDA / "fig5_correlaciones.png")
    plt.close(fig)


def main() -> None:
    params = yaml.safe_load(open(RAIZ / "params.yaml", encoding="utf-8"))
    proc = params["procesamiento"]
    SALIDA.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(RAIZ / params["datos"]["archivo_procesado"], parse_dates=["fecha_ingreso"])

    res = resumen_variables(df)
    res.to_csv(SALIDA / "resumen_variables.csv", index=False)

    desenlaces = pd.DataFrame([
        {"desenlace": nombre, "variable": var, "n_con_dato": int(df[var].notna().sum()),
         "eventos": int(df[var].sum()), "porcentaje": round(df[var].mean() * 100, 1)}
        for var, nombre in DESENLACES.items()
    ])
    desenlaces.to_csv(SALIDA / "desenlaces.csv", index=False)

    per = tabla_periodos(df)
    per.to_csv(SALIDA / "ingresos_por_periodo.csv", index=False)

    metricas = {
        "pacientes": int(len(df)),
        "predictores": int(len(df.columns) - len(NO_PREDICTORES)),
        "variables_con_mas_30pct_faltante": int((res["pct_faltante"] > 30).sum()),
        "estancia_mediana_dias": float(df["dias_estancia"].median()),
        **{f"pct_{v}": float(round(df[v].mean() * 100, 1)) for v in DESENLACES},
        **{f"n_{k}": int(v) for k, v in df["particion_temporal"].value_counts().items()},
    }
    json.dump(metricas, open(SALIDA / "metricas_eda.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    fig_faltantes(res)
    fig_estancia(df, proc["umbral_estancia_prolongada_dias"])
    fig_periodos(per, proc["fecha_corte_temporal"])
    fig_variables_por_mortalidad(df)
    fig_correlaciones(df)

    print(json.dumps(metricas, indent=2, ensure_ascii=False))
    print(f"Tablas y figuras en {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
