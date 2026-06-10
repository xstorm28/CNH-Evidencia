import dash
from dash import html, dcc, register_page, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# REGISTRAR PÁGINA
register_page(__name__, path='/pronosticos', name='Pronósticos', order=5)

# --- 1. CONFIGURACIÓN DE ESTILO Y COLORES ---
CNH_ROJO = "#A4242C"
CNH_OSCURO = "#242424"
CNH_VINO = "#482024"
CNH_GRIS = "#A0A0A0"
CNH_GRIS_CLARO = "#E0E0E0"
CNH_FONDO = "#FAFAFA"
BLANCO = "#FFFFFF"

# --- 2. DATOS ESTRATÉGICOS (TU LÓGICA) ---
MESES_ROADMAP = ["Hoy\n(Jun 2026)", "3 meses\n(Sep 2026)", "6 meses\n(Dic 2026)", "9 meses\n(Mar 2027)"]
COLORES_PUNTOS = [CNH_GRIS, "#8B6060", CNH_VINO, CNH_ROJO]

# --- 3. FUNCIONES AUXILIARES ---
def crear_kpi_estrategico(titulo, valor, color):
    return dbc.Card(dbc.CardBody([
        html.H6(titulo, className="text-muted text-center small mb-2", style={"height": "30px"}),
        html.H2(valor, className="fw-bold text-center mb-0", style={"color": color}),
    ]), style={"borderLeft": f"5px solid {color}", "boxShadow": "0 2px 4px rgba(0,0,0,0.05)"})

# --- 4. LAYOUT DE LA PÁGINA ---
layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H2("Futuro Alternativo: Hoja de Ruta Estratégica", className="fw-bold", style={"color": CNH_OSCURO}),
            html.P("Simulación de impacto basada en la implementación de las propuestas de servicio móvil y trazabilidad.", className="text-muted")
        ], width=8),
        dbc.Col([
            dcc.Tabs(id="tabs-estrategia", value='tab-movil', children=[
                dcc.Tab(label='Servicio Móvil', value='tab-movil'),
                dcc.Tab(label='Dark Data', value='tab-dark'),
            ], style={"height": "40px"})
        ], width=4)
    ], className="mb-4 align-items-end"),

    # Contenedor de KPIs (Se actualiza con el Tab)
    dbc.Row(id='contenedor-kpis-pronostico', className="mb-4"),

    # Contenedor de Gráfica Principal
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader(id='titulo-grafica-pronostico', className="fw-bold bg-white"),
            dbc.CardBody(dcc.Graph(id='grafica-roadmap-impacto', style={"height": "500px"}))
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)"}), width=12)
    ], className="mb-5"),

    # Footer Informativo
    dbc.Row([
        dbc.Col(html.Div([
            html.I(className="fa-solid fa-circle-info me-2"),
            html.Small("Las metas presentadas son objetivos explícitos del documento estratégico de trazabilidad 2026-2027.")
        ], className="text-muted text-center p-3", style={"backgroundColor": CNH_GRIS_CLARO, "borderRadius": "10px"}), width=12)
    ])
])

# --- 5. CALLBACK INTERACTIVO ---
@callback(
    [Output('contenedor-kpis-pronostico', 'children'),
     Output('titulo-grafica-pronostico', 'children'),
     Output('grafica-roadmap-impacto', 'figure')],
    [Input('tabs-estrategia', 'value')]
)
def actualizar_pronosticos(tab_seleccionado):
    
    if tab_seleccionado == 'tab-movil':
        # --- LÓGICA PROPUESTA 1: SERVICIO MÓVIL ---
        kpis = [
            crear_kpi_estrategico("Reducción de Desfase", "-830h", CNH_ROJO),
            crear_kpi_estrategico("Captura de Servicios", "+26.3 pp", CNH_VINO),
            crear_kpi_estrategico("Servicios Móviles / Mes", "50", CNH_GRIS),
        ]
        titulo = "¿Qué cambia si implementamos el servicio móvil proactivo?"
        
        # Datos
        desfase_g4 = [1130, 950, 600, 300]
        pct_cap_g4 = [3.7, 10.0, 18.0, 30.0]
        
        fig = make_subplots(rows=1, cols=2, 
                            subplot_titles=("Reducción del desfase — Uso Alto", "Servicios capturados en ventana"),
                            horizontal_spacing=0.12)
        
        # Panel A
        fig.add_trace(go.Scatter(
            x=MESES_ROADMAP, y=desfase_g4, mode="lines+markers+text",
            line=dict(color=CNH_ROJO, width=4),
            marker=dict(size=14, color=COLORES_PUNTOS, line=dict(color=CNH_OSCURO, width=2)),
            text=[f"{d:,}h" for d in desfase_g4], textposition="bottom center",
            fill="tozeroy", fillcolor="rgba(164,36,44,0.05)",
            name="Desfase", showlegend=False
        ), row=1, col=1)
        fig.add_hline(y=300, line_dash="dash", line_color=CNH_ROJO, annotation_text="Meta: <300h", row=1, col=1)

        # Panel B
        fig.add_trace(go.Scatter(
            x=MESES_ROADMAP, y=pct_cap_g4, mode="lines+markers+text",
            line=dict(color=CNH_ROJO, width=4),
            marker=dict(size=14, color=COLORES_PUNTOS, line=dict(color=CNH_OSCURO, width=2)),
            text=[f"{p}%" for p in pct_cap_g4], textposition="top center",
            fill="tozeroy", fillcolor="rgba(164,36,44,0.05)",
            name="Captura", showlegend=False
        ), row=1, col=2)
        fig.add_hline(y=30, line_dash="dash", line_color=CNH_ROJO, annotation_text="Meta: 30%", row=1, col=2)

    else:
        # --- LÓGICA PROPUESTA 2: DARK DATA ---
        kpis = [
            crear_kpi_estrategico("Reducción Dark Data", "-41.8 pp", CNH_ROJO),
            crear_kpi_estrategico("Equipos Rescatados", "2,500", CNH_VINO),
            crear_kpi_estrategico("Meta Completitud", ">85%", CNH_GRIS),
        ]
        titulo = "¿Qué cambia si corregimos los puntos ciegos de la red?"
        
        dark_global = [91.8, 75.0, 62.0, 50.0]
        comp_top3 = [8.6, 70.0, 78.0, 85.0]

        fig = make_subplots(rows=1, cols=2, 
                            subplot_titles=("Reducción de Dark Data Global", "Completitud en Distribuidores Críticos"),
                            horizontal_spacing=0.12)
        
        # Panel A
        fig.add_trace(go.Scatter(
            x=MESES_ROADMAP, y=dark_global, mode="lines+markers+text",
            line=dict(color=CNH_VINO, width=4),
            marker=dict(size=14, color=COLORES_PUNTOS, line=dict(color=CNH_OSCURO, width=2)),
            text=[f"{v}%" for v in dark_global], textposition="top center",
            fill="tozeroy", fillcolor="rgba(72,32,36,0.05)",
            name="Dark Data", showlegend=False
        ), row=1, col=1)
        fig.add_hline(y=50, line_dash="dash", line_color=CNH_VINO, annotation_text="Meta: <50%", row=1, col=1)

        # Panel B
        fig.add_trace(go.Scatter(
            x=MESES_ROADMAP, y=comp_top3, mode="lines+markers+text",
            line=dict(color=CNH_VINO, width=4),
            marker=dict(size=14, color=COLORES_PUNTOS, line=dict(color=CNH_OSCURO, width=2)),
            text=[f"{v}%" for v in comp_top3], textposition="bottom center",
            fill="tozeroy", fillcolor="rgba(72,32,36,0.05)",
            name="Completitud", showlegend=False
        ), row=1, col=2)
        fig.add_hline(y=80, line_dash="dash", line_color=CNH_VINO, annotation_text="Meta: >80%", row=1, col=2)

    # Estilo común para ambas gráficas
    fig.update_layout(
        template="plotly_white",
        margin=dict(t=60, b=40, l=60, r=40),
        font=dict(family="Arial")
    )
    fig.update_yaxes(gridcolor=CNH_GRIS_CLARO, gridwidth=0.5)
    fig.update_xaxes(showgrid=False)

    # Convertir lista de KPIs a columnas de Dash
    kpi_cols = [dbc.Col(k, width=4) for k in kpis]

    return [kpi_cols, titulo, fig]