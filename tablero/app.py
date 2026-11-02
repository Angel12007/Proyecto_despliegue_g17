"""UCI Analytics – tablero del proyecto G17.

Tres pantallas:
  1. Predicción individual: riesgo de estancia >= 7 días y de muerte en UCI,
     días y costo esperados, y qué datos del paciente mueven el riesgo.
  2. Planificación de camas: lista de pacientes ordenada por riesgo, con
     días-cama y costo esperados (censo histórico de un día, ingresos de un
     periodo o una lista propia cargada desde archivo).
  3. Capacidad y costos: indicadores históricos con filtros, concentración de
     días-cama por riesgo y costos de referencia.

Uso (desde la carpeta principal del repositorio):
    python tablero/app.py
y abrir http://127.0.0.1:8050
"""
from __future__ import annotations

import base64
import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dash_table, dcc, html, no_update

import config
import datos
import servicio_modelo as sm

AZUL = "#1f5f8b"
VERDE = "#1a8a7a"
ROJO = "#c0392b"
GRIS = "#8a99a8"
COLOR_RIESGO = {"Alto": ROJO, "Intermedio": "#d68910", "Bajo": VERDE}

app = Dash(__name__, title="UCI Analytics", suppress_callback_exceptions=True)
server = app.server  # para desplegar con gunicorn más adelante


# ----------------------------------------------------------------------------
# Utilidades de formato
# ----------------------------------------------------------------------------
def miles(x, dec=0) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    s = f"{x:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pesos(x) -> str:
    return "$ " + miles(x)


def millones(x) -> str:
    return "$ " + miles(x / 1e6, 0) + " M"


def tarjeta(titulo, valor, nota="", color=AZUL, extra=None):
    hijos = [html.Div(titulo, className="tarjeta-titulo"),
             html.Div(valor, className="tarjeta-valor", style={"color": color}),
             html.Div(nota, className="tarjeta-nota")]
    if extra is not None:
        hijos.append(extra)
    return html.Div(hijos, className="tarjeta")


def grafica_base(fig: go.Figure, alto=320) -> go.Figure:
    fig.update_layout(height=alto, margin=dict(l=40, r=20, t=40, b=40), paper_bgcolor="white",
                      plot_bgcolor="white", font=dict(family="Segoe UI, Arial", size=12, color="#1d2b3a"),
                      legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(showgrid=False, linecolor="#c9d3dd")
    fig.update_yaxes(gridcolor="#eef2f6", linecolor="#c9d3dd")
    return fig


# ----------------------------------------------------------------------------
# Estructura general
# ----------------------------------------------------------------------------
MENU = [("/", "Predicción individual"), ("/planificacion", "Planificación de camas"),
        ("/capacidad", "Capacidad y costos")]

app.layout = html.Div([
    dcc.Location(id="url"),
    dcc.Store(id="tarifas", storage_type="session",
              data={"uci": config.TARIFA_UCI, "intermedio": config.TARIFA_INTERMEDIO}),
    dcc.Store(id="lista", storage_type="session", data=[]),
    html.Div([
        html.Div([html.Span("✚", className="logo-cruz"), "UCI Analytics"], className="logo"),
        html.Div(id="menu", className="menu"),
        html.Div([
            html.Div("Modelo en uso", className="lateral-titulo"),
            html.Div(id="info-modelo", className="lateral-texto"),
            html.Div("Herramienta de apoyo. No sustituye la valoración médica ni decide la asignación de camas.",
                     className="lateral-aviso"),
        ], className="lateral-pie"),
    ], className="lateral"),
    html.Div(id="pagina", className="contenido"),
], className="marco")


@app.callback(Output("menu", "children"), Output("pagina", "children"), Output("info-modelo", "children"),
              Input("url", "pathname"))
def navegar(ruta):
    ruta = ruta if ruta in dict(MENU) else "/"
    menu = [dcc.Link(t, href=h, className="menu-item activo" if h == ruta else "menu-item") for h, t in MENU]
    pagina = {"/": pagina_prediccion, "/planificacion": pagina_planificacion,
              "/capacidad": pagina_capacidad}[ruta]()
    me, mm = sm.cargar_modelo("estancia_prolongada"), sm.cargar_modelo("mortality")
    info = [html.Div(me["nombre"]),
            html.Div(f"AUROC prueba: estancia {miles(me['metricas']['auroc_prueba'], 3)} · "
                     f"muerte {miles(mm['metricas']['auroc_prueba'], 3)}")]
    return menu, pagina, info


# ----------------------------------------------------------------------------
# Pantalla 1: predicción individual
# ----------------------------------------------------------------------------
def campo(var):
    _, etiqueta, tipo, opciones = next(c for c in config.CAMPOS if c[0] == var)
    if tipo == "num":
        control = dcc.Input(id={"campo": var}, type="number", min=opciones[0], max=opciones[1],
                            placeholder="sin dato", className="entrada", debounce=True)
    else:
        control = dcc.Dropdown(id={"campo": var}, options=[{"label": k, "value": v} for k, v in opciones.items()],
                               placeholder="sin dato", clearable=True, className="desplegable")
    return html.Div([html.Label(etiqueta, className="etiqueta"), control], className="campo")


def pagina_prediccion():
    grupos = [html.Div([html.Div(t, className="grupo-titulo"),
                        html.Div([campo(v) for v in vs], className="rejilla-campos")], className="grupo")
              for t, vs in config.GRUPOS_FORMULARIO]
    return html.Div([
        html.H1("Predicción al ingreso por paciente"),
        html.P("Información de las primeras 24 horas en la UCI. Los campos vacíos se completan con la "
               "imputación del modelo y se avisa cuáles fueron.", className="subtitulo"),
        html.Div([
            html.Div([
                html.Div("Información clínica · primeras 24 horas", className="panel-titulo"),
                *grupos,
                html.Div([
                    html.Button("Calcular riesgo", id="btn-calcular", className="boton principal"),
                    html.Button("Cargar ejemplo", id="btn-ejemplo", className="boton"),
                    html.Button("Limpiar", id="btn-limpiar", className="boton"),
                    html.Button("Agregar a mi lista", id="btn-agregar", className="boton"),
                    html.Span(id="estado-agregar", className="nota"),
                ], className="botones"),
            ], className="panel formulario"),
            html.Div(id="resultado", className="columna-resultado", children=[
                html.Div("Complete los datos y pulse «Calcular riesgo».", className="panel vacio")]),
        ], className="dos-columnas"),
    ])


@app.callback([Output({"campo": v}, "value") for v in config.VARIABLES],
              Input("btn-ejemplo", "n_clicks"), Input("btn-limpiar", "n_clicks"), prevent_initial_call=True)
def llenar(_, __):
    if ctx.triggered_id == "btn-ejemplo":
        return [config.EJEMPLO.get(v) for v in config.VARIABLES]
    return [None for _ in config.VARIABLES]


@app.callback(Output("resultado", "children"), Input("btn-calcular", "n_clicks"),
              [State({"campo": v}, "value") for v in config.VARIABLES], State("tarifas", "data"),
              prevent_initial_call=True)
def calcular(_, *valores):
    *valores, tarifas = valores
    paciente = {v: (np.nan if x is None else x) for v, x in zip(config.VARIABLES, valores)}
    faltantes = [config.ETIQUETAS[v] for v, x in paciente.items() if pd.isna(x)]
    if len(faltantes) > 7:
        return html.Div("Faltan demasiados datos (más de la mitad). Complete al menos edad, escalas y soportes.",
                        className="panel vacio alerta")
    X = pd.DataFrame([paciente])
    pred = sm.predecir_tabla(X).iloc[0]
    est = datos.estimador()
    dias = float(est.totales([pred["p_estancia"]])[0])
    vent = paciente["ventilatory_support"]
    tarifa = tarifas["uci"] if vent == 1 else tarifas["intermedio"]
    nota_tarifa = "tarifa UCI" if vent == 1 else "tarifa intermedio"

    def bloque(titulo, p, riesgo, desenlace, color):
        contrib = sm.contribuciones(paciente, desenlace)
        fig = go.Figure(go.Bar(x=contrib["efecto"] * 100, y=contrib["variable"], orientation="h",
                               marker_color=[ROJO if e > 0 else VERDE for e in contrib["efecto"]]))
        fig.update_layout(title=dict(text="Qué datos mueven el riesgo (puntos porcentuales)", font=dict(size=12)))
        fig.update_yaxes(autorange="reversed")
        return html.Div([
            html.Div(titulo, className="panel-titulo"),
            html.Div([html.Span(f"{miles(100 * p, 0)} %", className="numero-grande", style={"color": color}),
                      html.Span(riesgo, className="insignia", style={"background": COLOR_RIESGO[riesgo]})],
                     className="fila-numero"),
            dcc.Graph(figure=grafica_base(fig, 210), config={"displayModeBar": False}),
        ], className="panel resultado")

    return [
        bloque("Probabilidad de estancia ≥ 7 días", pred["p_estancia"], pred["riesgo_estancia"],
               "estancia_prolongada", AZUL),
        bloque("Riesgo de muerte en UCI", pred["p_muerte"], pred["riesgo_muerte"], "mortality", VERDE),
        html.Div([
            tarjeta("Días de estancia esperados", miles(dias, 1), "promedio ponderado por el riesgo"),
            tarjeta("Costo de referencia esperado", millones(dias * tarifa), f"{nota_tarifa} · pesos 2020"),
        ], className="fila-tarjetas dos"),
        html.Div(("Datos imputados por el modelo: " + ", ".join(faltantes)) if faltantes else
                 "Todos los datos fueron ingresados.", className="nota-imputados"),
        html.Div("Riesgo alto = 20 % de pacientes con mayor probabilidad en la cohorte de entrenamiento. "
                 "No sustituye la valoración médica.", className="nota"),
    ]


@app.callback(Output("lista", "data", allow_duplicate=True), Output("estado-agregar", "children"),
              Input("btn-agregar", "n_clicks"), [State({"campo": v}, "value") for v in config.VARIABLES],
              State("lista", "data"), prevent_initial_call=True)
def agregar(n_clicks, *valores):
    *valores, lista = valores
    if not n_clicks:  # Dash dispara el callback al dibujar la pantalla; se ignora
        return no_update, no_update
    if all(v is None for v in valores):
        return no_update, "Complete los datos del paciente antes de agregarlo."
    lista = list(lista or [])
    lista.append({"paciente": f"Paciente {len(lista) + 1}", **dict(zip(config.VARIABLES, valores))})
    return lista, f"Agregado. Mi lista tiene {len(lista)} paciente(s): véala en Planificación de camas."


# ----------------------------------------------------------------------------
# Pantalla 2: planificación de camas
# ----------------------------------------------------------------------------
def pagina_planificacion():
    ini, fin = datos.rango_prueba()
    return html.Div([
        html.H1("Planificación de camas"),
        html.P("Pacientes ordenados por riesgo, con los días-cama y el costo que se esperan. El histórico usa "
               "solo pacientes del periodo de prueba (jul-2024 en adelante), que el modelo no vio al entrenar, "
               "y permite comparar lo esperado con lo que realmente ocurrió.", className="subtitulo"),
        html.Div([
            dcc.RadioItems(id="fuente", value="censo", className="radio", inline=True, options=[
                {"label": "Censo de un día", "value": "censo"},
                {"label": "Ingresos de un periodo", "value": "periodo"},
                {"label": "Mi lista", "value": "lista"}]),
            html.Div(dcc.DatePickerSingle(id="fecha", date=pd.Timestamp("2024-08-15").date(),
                                          min_date_allowed=ini.date(), max_date_allowed=fin.date(),
                                          display_format="DD/MM/YYYY"), id="caja-fecha"),
            html.Div(dcc.DatePickerRange(id="periodo", start_date=pd.Timestamp("2024-07-01").date(),
                                         end_date=pd.Timestamp("2024-07-31").date(),
                                         min_date_allowed=ini.date(), max_date_allowed=fin.date(),
                                         display_format="DD/MM/YYYY"), id="caja-periodo"),
            html.Div([
                dcc.Upload(id="archivo", children=html.Button("Cargar CSV de pacientes", className="boton"),
                           accept=".csv"),
                html.Button("Descargar plantilla", id="btn-plantilla", className="boton"),
                dcc.Download(id="descarga-plantilla"),
                html.Span(id="estado-archivo", className="nota"),
            ], id="caja-lista", className="fila-botones"),
        ], className="panel controles"),
        html.Div(id="plan-tarjetas", className="fila-tarjetas cuatro"),
        html.Div([
            html.Div([html.Div("Pacientes ordenados por riesgo de estancia prolongada", className="panel-titulo"),
                      html.Div(id="plan-tabla")], className="panel ancho"),
        ]),
        html.Div(id="plan-nota", className="nota"),
    ])


@app.callback(Output("caja-fecha", "style"), Output("caja-periodo", "style"), Output("caja-lista", "style"),
              Input("fuente", "value"))
def mostrar_controles(fuente):
    ver, ocultar = {"display": "block"}, {"display": "none"}
    return (ver if fuente == "censo" else ocultar, ver if fuente == "periodo" else ocultar,
            {"display": "flex"} if fuente == "lista" else ocultar)


@app.callback(Output("descarga-plantilla", "data"), Input("btn-plantilla", "n_clicks"), prevent_initial_call=True)
def plantilla(_):
    ejemplo = pd.DataFrame([{"paciente": "Cama 1", **config.EJEMPLO},
                            {"paciente": "Cama 2", **{v: None for v in config.VARIABLES}}])
    return dcc.send_data_frame(ejemplo.to_csv, "plantilla_pacientes_uci.csv", index=False)


@app.callback(Output("lista", "data"), Output("estado-archivo", "children"), Input("archivo", "contents"),
              State("archivo", "filename"), State("lista", "data"), prevent_initial_call=True)
def leer_archivo(contenido, nombre, lista):
    try:
        _, datos_b64 = contenido.split(",", 1)
        df = pd.read_csv(io.StringIO(base64.b64decode(datos_b64).decode("utf-8-sig")))
    except Exception as e:  # archivo dañado o sin formato CSV
        return no_update, f"No se pudo leer {nombre}: {e}"
    faltan = [v for v in config.VARIABLES if v not in df.columns]
    if len(faltan) == len(config.VARIABLES):
        return no_update, "El archivo no tiene las columnas de la plantilla."
    df = df.replace({np.nan: None})
    lista = list(lista or []) + df.to_dict("records")
    return lista, f"{nombre}: {len(df)} pacientes cargados. Mi lista tiene {len(lista)} en total."


@app.callback(Output("plan-tarjetas", "children"), Output("plan-tabla", "children"), Output("plan-nota", "children"),
              Input("fuente", "value"), Input("fecha", "date"), Input("periodo", "start_date"),
              Input("periodo", "end_date"), Input("lista", "data"), State("tarifas", "data"))
def actualizar_plan(fuente, fecha, ini, fin, lista, tarifas):
    if fuente == "censo":
        df = datos.censo(fecha, tarifas)
        dias_e, dias_r = "dias_restantes_esperados", "dias_restantes_reales"
        nota = (f"Censo del {pd.Timestamp(fecha):%d/%m/%Y}: pacientes de la cohorte hospitalizados ese día. "
                "Días restantes esperados = estimación según el riesgo y los días que ya lleva cada paciente. "
                "La cohorte del estudio es una parte de los ingresos de la UCI, por eso el censo es menor "
                "que las 28 camas.")
    elif fuente == "periodo":
        df = datos.ingresos_periodo(ini, fin, tarifas)
        dias_e, dias_r = "dias_esperados", "dias_estancia"
        nota = "Ingresos del periodo: días-cama esperados desde el ingreso frente a los que realmente se usaron."
    else:
        df = datos.lista_propia(lista, tarifas)
        dias_e, dias_r = "dias_esperados", None
        nota = ("Mi lista: pacientes cargados desde un archivo CSV (formato de la plantilla) o agregados desde "
                "la pantalla de predicción. Días y costo esperados desde el ingreso.")
    if df.empty:
        return [tarjeta("Pacientes", "0")], html.Div("No hay pacientes para mostrar.", className="vacio"), nota

    real = dias_r is not None
    tarjetas = [
        tarjeta("Pacientes", miles(len(df)), "en la selección"),
        tarjeta("Días-cama esperados", miles(df[dias_e].sum(), 0),
                f"reales: {miles(df[dias_r].sum(), 0)}" if real else "estimación del modelo"),
        tarjeta("Estancias ≥ 7 días esperadas", miles(df["p_estancia"].sum(), 1),
                (f"reales: {int(df['estancia_prolongada'].sum())}" if real and fuente != "censo" else
                 f"pacientes en riesgo alto: {(df['riesgo_estancia'] == 'Alto').sum()}")),
        tarjeta("Costo de referencia esperado", millones(df["costo_esperado"].sum()),
                f"real: {millones(df['costo_real'].sum())}" if real else "pesos de 2020"),
    ]
    tabla = pd.DataFrame({
        "Paciente": df["paciente"] if "paciente" in df else df.get("record_id"),
        **({"Ingreso": df["fecha_ingreso"].dt.strftime("%d/%m/%Y")} if "fecha_ingreso" in df else {}),
        **({"Días en UCI": df["dias_transcurridos"]} if "dias_transcurridos" in df else {}),
        "P(estancia ≥ 7 d) %": (100 * df["p_estancia"]).round(0),
        "Riesgo estancia": df["riesgo_estancia"],
        "P(muerte) %": (100 * df["p_muerte"]).round(0),
        "Riesgo muerte": df["riesgo_muerte"],
        "Días esperados": df[dias_e].round(1),
        **({"Días reales": df[dias_r]} if real else {}),
        "Costo esperado (M$)": (df["costo_esperado"] / 1e6).round(1),
        "Ventilación": df["ventilatory_support"].map({1: "Sí", 0: "No"}),
    })
    estilos = [{"if": {"filter_query": f'{{{col}}} = "{r}"', "column_id": col},
                "backgroundColor": c, "color": "white", "fontWeight": "600"}
               for col in ["Riesgo estancia", "Riesgo muerte"] for r, c in COLOR_RIESGO.items()]
    tabla_dash = dash_table.DataTable(
        data=tabla.to_dict("records"), columns=[{"name": c, "id": c} for c in tabla.columns],
        sort_action="native", page_size=12, style_as_list_view=True, style_table={"overflowX": "auto"},
        style_header={"backgroundColor": "#eef3f8", "fontWeight": "600", "border": "none"},
        style_cell={"fontFamily": "Segoe UI, Arial", "fontSize": 13, "padding": "6px 10px", "textAlign": "center"},
        style_data_conditional=estilos)
    return tarjetas, tabla_dash, nota


# ----------------------------------------------------------------------------
# Pantalla 3: capacidad y costos
# ----------------------------------------------------------------------------
def pagina_capacidad():
    df = datos.base()
    return html.Div([
        html.H1("Capacidad y costos"),
        html.P("Indicadores de la cohorte con filtros, concentración de días-cama según el riesgo y costos de "
               "referencia.", className="subtitulo"),
        html.Div([
            html.Div([html.Label("Origen del tumor", className="etiqueta"),
                      dcc.Checklist(id="f-origen", options=["Sólido", "Hematológico"],
                                    value=["Sólido", "Hematológico"], inline=True, className="radio")]),
            html.Div([html.Label("Tipo de ingreso", className="etiqueta"),
                      dcc.Checklist(id="f-ingreso", options=["Médico", "Quirúrgico"],
                                    value=["Médico", "Quirúrgico"], inline=True, className="radio")]),
            html.Div([html.Label("Fecha de ingreso", className="etiqueta"),
                      dcc.DatePickerRange(id="f-fechas", start_date=df["fecha_ingreso"].min().date(),
                                          end_date=df["fecha_ingreso"].max().date(), display_format="DD/MM/YYYY")]),
            html.Div([html.Label("Tarifa día UCI ($)", className="etiqueta"),
                      dcc.Input(id="t-uci", type="number", value=config.TARIFA_UCI, className="entrada",
                                debounce=True)]),
            html.Div([html.Label("Tarifa día intermedio ($)", className="etiqueta"),
                      dcc.Input(id="t-intermedio", type="number", value=config.TARIFA_INTERMEDIO,
                                className="entrada", debounce=True)]),
        ], className="panel controles filtros"),
        html.Div(id="cap-tarjetas", className="fila-tarjetas cuatro"),
        html.Div(id="cap-costos", className="fila-tarjetas tres"),
        html.Div([
            html.Div([html.Div("Concentración de días-cama según el riesgo (pacientes de prueba)",
                               className="panel-titulo"), dcc.Graph(id="g-concentracion")], className="panel"),
            html.Div([html.Div("Días-cama y costo por grupo de riesgo", className="panel-titulo"),
                      dcc.Graph(id="g-grupos")], className="panel"),
        ], className="dos-columnas iguales"),
        html.Div([
            html.Div([html.Div("Tendencia por semestre", className="panel-titulo"), dcc.Graph(id="g-tendencia")],
                     className="panel"),
            html.Div([html.Div("Días-cama de pacientes con soporte ventilatorio", className="panel-titulo"),
                      html.Div(id="cap-vent")], className="panel"),
        ], className="dos-columnas iguales"),
        html.Div(config.FUENTE_TARIFAS + " La tarifa se asigna según el soporte ventilatorio en las primeras 24 h "
                 "(supuesto del equipo).", className="nota"),
    ])


@app.callback(Output("tarifas", "data"), Input("t-uci", "value"), Input("t-intermedio", "value"),
              prevent_initial_call=True)
def guardar_tarifas(uci, inter):
    return {"uci": uci or config.TARIFA_UCI, "intermedio": inter or config.TARIFA_INTERMEDIO}


@app.callback(Output("cap-tarjetas", "children"), Output("cap-costos", "children"), Output("g-concentracion", "figure"),
              Output("g-grupos", "figure"), Output("g-tendencia", "figure"), Output("cap-vent", "children"),
              Input("f-origen", "value"), Input("f-ingreso", "value"), Input("f-fechas", "start_date"),
              Input("f-fechas", "end_date"), Input("tarifas", "data"))
def actualizar_capacidad(origen, ingreso, ini, fin, tarifas):
    df = datos.filtrar(origen or [], ingreso or [], ini, fin)
    k = datos.kpis(df, tarifas)
    tarjetas = [tarjeta("Pacientes", miles(k["pacientes"]), "en la selección"),
                tarjeta("Días-cama", miles(k["dias_cama"]), "consumo acumulado"),
                tarjeta("% estancia ≥ 7 días", f"{miles(k['pct_prolongada'], 1)} %", "de los pacientes"),
                tarjeta("Mortalidad en UCI", f"{miles(k['mortalidad'], 1)} %", "de los pacientes")]
    costos = [tarjeta("Costo de referencia total", millones(k["costo_total"]), "días-cama × tarifa · pesos 2020"),
              tarjeta("Costo de estancias ≥ 7 días", millones(k["costo_prolongadas"]),
                      f"{miles(100 * k['costo_prolongadas'] / k['costo_total'] if k['costo_total'] else np.nan, 0)} % "
                      "del costo total"),
              tarjeta("Costo del 20 % de mayor riesgo", millones(k["costo_top20"]),
                      f"{miles(100 * k['costo_top20'] / k['costo_total'] if k['costo_total'] else np.nan, 0)} % "
                      "del costo total")]

    prueba = df[df["particion_temporal"] == "prueba"]
    fig_c = go.Figure()
    for col, nombre, color, dash_ in [("p_estancia", "Modelo", AZUL, "solid"), ("sapsiii", "SAPS III", GRIS, "dot")]:
        c = datos.curva_concentracion(prueba, col)
        fig_c.add_trace(go.Scatter(x=c["pct_pacientes"], y=c["pct_dias"], name=nombre,
                                   line=dict(color=color, width=3, dash=dash_)))
    fig_c.add_trace(go.Scatter(x=[0, 100], y=[0, 100], name="Al azar", line=dict(color="#c9d3dd", dash="dash")))
    fig_c.add_vline(x=20, line_dash="dash", line_color=ROJO, annotation_text="20 %", annotation_position="top")
    fig_c.update_layout(xaxis_title="% de pacientes (de mayor a menor riesgo)", yaxis_title="% de días-cama")

    grupos = df.assign(dias=df["dias_estancia"].fillna(0))
    grupos["costo"] = datos.costear(grupos, "dias", tarifas)
    g = grupos.groupby("riesgo_estancia").agg(pacientes=("record_id", "count"), dias=("dias", "sum"),
                                              costo=("costo", "sum")).reindex(["Bajo", "Intermedio", "Alto"]).fillna(0)
    fig_g = go.Figure()
    fig_g.add_trace(go.Bar(x=g.index, y=g["dias"], name="Días-cama", marker_color=[COLOR_RIESGO[i] for i in g.index],
                           text=[f"{miles(d)} días<br>{millones(c)}" for d, c in zip(g["dias"], g["costo"])],
                           textposition="outside"))
    fig_g.update_layout(showlegend=False, yaxis_title="Días-cama")

    t = datos.tendencia(df)
    fig_t = go.Figure()
    fig_t.add_trace(go.Bar(x=t["semestre"], y=t["ingresos"], name="Ingresos", marker_color="#d6e2ee", yaxis="y"))
    fig_t.add_trace(go.Scatter(x=t["semestre"], y=100 * t["prolongada"], name="% estancia ≥ 7 d",
                               line=dict(color=AZUL, width=3), yaxis="y2"))
    fig_t.add_trace(go.Scatter(x=t["semestre"], y=100 * t["mortalidad"], name="% mortalidad",
                               line=dict(color=ROJO, width=3), yaxis="y2"))
    fig_t.update_layout(yaxis=dict(title="Ingresos"), yaxis2=dict(title="%", overlaying="y", side="right",
                                                                  showgrid=False, tickformat=".0f", rangemode="tozero"))

    vent = html.Div([
        html.Div(f"{miles(k['dias_vent_pct'], 0)} % de días-cama", className="numero-grande", style={"color": AZUL}),
        html.Div(className="barra", children=html.Div(className="barra-relleno",
                                                       style={"width": f"{0 if np.isnan(k['dias_vent_pct']) else k['dias_vent_pct']:.0f}%"})),
        html.Div(f"los consume el {miles(k['pac_vent_pct'], 0)} % de los pacientes, que requirió soporte "
                 "ventilatorio en las primeras 24 horas.", className="tarjeta-nota"),
    ])
    return (tarjetas, costos, grafica_base(fig_c), grafica_base(fig_g), grafica_base(fig_t), vent)


if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
