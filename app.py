
CNH_ROJO       = "#A4242C"
CNH_ROJO_ALT   = "#A82024"
CNH_OSCURO     = "#242424"
CNH_VINO       = "#6B3030"
CNH_GRIS       = "#9E9E9E"
CNH_GRIS_CLARO = "#D4D0D0"
CNH_FONDO      = "#F7F4F4"
BLANCO         = "#FFFFFF"
FUENTE         = dict(family="Arial", size=12, color=CNH_OSCURO)

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# --- 1. SETUP ---
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.LUX],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

# --- 2. COLORES CNH ---
CNH_ROJO = "#A4242C"
CNH_OSCURO = "#242424"
CNH_VINO = "#482024"
CNH_GRIS = "#A0A0A0"
CNH_GRIS_CLARO = "#E0E0E0"
CNH_FONDO = "#FAFAFA"
BLANCO = "#FFFFFF"

# --- 3. DATOS Y CÁLCULOS (KPIs Bloque 1) ---
# Asegúrate de que el archivo 'df_total.xlsx' esté en la misma carpeta que este script
try:
    df_total = pd.read_excel('df_total.xlsx')
except Exception as e:
    print(f"Error al cargar el Excel: {e}")
    # DataFrame de respaldo por si no encuentra el archivo, para que no truene la app
    df_total = pd.DataFrame({'alias': ['A1'], 'servicio': ['Si']})

ID_EQUIPO = 'alias'

equipos_unicos = df_total[ID_EQUIPO].nunique()
# Asumiendo que la columna se llama 'servicio'. Ajusta si tiene otro nombre en tu Excel.
if 'servicio' in df_total.columns:
    equipos_con_servicio = df_total[df_total['servicio'].notna()][ID_EQUIPO].nunique()
else:
    equipos_con_servicio = 0

df_eq = df_total.groupby(ID_EQUIPO)['horometro'].max().reset_index()
df_eq['horometro'] = pd.to_numeric(df_eq['horometro'], errors='coerce').fillna(0).astype(int)

menos_300 = (df_eq['horometro'] < 300).sum()
pct_menos300 = (menos_300 / len(df_eq)) * 100

# --- 4. GRÁFICA 1: INTENSIDAD VS CAPTURA ---
segmentos = ["Uso Bajo", "Uso Medio", "Uso Alto"]
pct_retraso = [44.2, 65.1, 96.3]
desfase = [295, 434, 1130]
colores_g1 = [CNH_GRIS, CNH_VINO, CNH_ROJO]

fig1 = make_subplots(specs=[[{"secondary_y": True}]])

fig1.add_trace(go.Bar(
    x=segmentos, y=pct_retraso, name="% con retraso crítico",
    marker_color=colores_g1, marker_line_color=CNH_OSCURO, marker_line_width=1,
    text=[f"{v}%" for v in pct_retraso], textposition="inside",
    textfont=dict(size=18, color=BLANCO, family="Arial Black"),
), secondary_y=False)

fig1.add_trace(go.Scatter(
    x=segmentos, y=desfase, name="Desfase promedio (h)",
    mode="lines+markers",
    line=dict(color=CNH_OSCURO, width=2.5, dash="dash"),
    marker=dict(symbol="diamond", size=12, color=BLANCO, line=dict(color=CNH_OSCURO, width=2.5)),
), secondary_y=True)

fig1.update_layout(
    plot_bgcolor=BLANCO, paper_bgcolor=BLANCO, 
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    hovermode="x unified", margin=dict(t=40, b=40, l=40, r=40), height=400,
)
fig1.update_yaxes(title_text="% equipos con retraso crítico (>100h)", ticksuffix="%", range=[0, 115], gridcolor=CNH_GRIS_CLARO, secondary_y=False)
fig1.update_yaxes(title_text="Desfase promedio (horas)", ticksuffix="h", range=[0, 1500], gridcolor="rgba(0,0,0,0)", secondary_y=True)
fig1.update_xaxes(showgrid=False)

# --- 5. ESTILOS Y FUNCIONES AUXILIARES ---
SIDEBAR_STYLE = {
    "position": "fixed", "top": 0, "left": 0, "bottom": 0,
    "width": "16rem", "padding": "2rem 1rem", "background-color": CNH_OSCURO,
}
CONTENT_STYLE = {
    "margin-left": "18rem", "margin-right": "2rem", "padding": "2rem 1rem",
    "background-color": CNH_FONDO, "minHeight": "100vh"
}

def crear_kpi_card(titulo, valor, color_borde):
    return dbc.Card(
        dbc.CardBody([
            html.H6(titulo, className="text-muted text-uppercase", style={"fontSize": "12px"}),
            html.H2(valor, className="fw-bold mb-0", style={"color": color_borde})
        ]),
        style={"borderLeft": f"5px solid {color_borde}", "boxShadow": "0 4px 6px rgba(0,0,0,0.05)"}
    )

# --- 6. NAVEGACIÓN (SIDEBAR) ---
sidebar = html.Div([
    html.Div(html.Img(src="/assets/logo.png", style={"width": "100%", "maxWidth": "150px"}), className="text-center mb-4"),
    html.Hr(style={"borderColor": CNH_ROJO}),
    dbc.Nav([
        dbc.NavLink("Reporte", href="/", active="exact"),
        dbc.NavLink("Flota", href="/flota", active="exact"),
        dbc.NavLink("Región", href="/region", active="exact"),
        dbc.NavLink("Incumplimiento", href="/incumplimiento", active="exact"),
        dbc.NavLink("Pronósticos", href="/pronosticos", active="exact"),
    ], vertical=True, pills=True),
], style=SIDEBAR_STYLE)

# --- 7. CONTENIDO PÁGINA REPORTE ---
content = html.Div(id="page-content", children=[
    html.H2("Insight: Intensidad vs Captura", className="mb-4 fw-bold", style={"color": CNH_OSCURO}),
    
    # SECCIÓN 1: EL PANORAMA GENERAL
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Análisis de rentabilidad fugada (Retraso crítico por segmento)", className="fw-bold bg-white"),
                dbc.CardBody(dcc.Graph(figure=fig1, config={'displayModeBar': False}))
            ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)"}), 
            width=9 
        ),
        dbc.Col([
            crear_kpi_card("Equipos Analizados", f"{equipos_unicos:,}", CNH_OSCURO),
            html.Div(className="mb-3"), # Espaciador
            crear_kpi_card("Servicios Registrados", f"{equipos_con_servicio:,}", CNH_VINO),
            html.Div(className="mb-3"), # Espaciador
            crear_kpi_card("Equipos < 300h", f"{menos_300:,}", CNH_ROJO),
            html.Div(className="mb-3"), # Espaciador
            crear_kpi_card("% Equipos < 300h", f"{pct_menos300:.1f}%", CNH_OSCURO),
        ], width=3, className="d-flex flex-column justify-content-between")
    ], className="mb-5 align-items-stretch"),
    
    # SECCIÓN 2: EL FOCO DEL PROBLEMA (Sobreexplotación)
    html.Hr(className="mb-5"),
    dbc.Row([
        dbc.Col([
            # Estos KPIs están fijos por el momento hasta que los calculemos con la gráfica 2
            crear_kpi_card("Desfase > 100h", "21,072", CNH_ROJO),
            html.Div(className="mb-4"),
            crear_kpi_card("Desfase > 300h", "16,864", CNH_VINO),
        ], width=3, className="d-flex flex-column justify-content-center"),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Sobreexplotación por equipos", className="card-title fw-bold"),
                    html.Div(id="grafica-sobreexplotacion-placeholder", children=[
                        html.P("Esperando código de la segunda gráfica...", className="text-muted mt-5 text-center")
                    ])
                ]), 
                style={"minHeight": "400px", "boxShadow": "0 4px 15px rgba(0,0,0,0.1)"}
            ), 
            width=9
        )
    ]),
], style=CONTENT_STYLE)

app.layout = html.Div([dcc.Location(id="url"), sidebar, content])

if __name__ == "__main__":
    app.run(debug=True)