import dash
from dash import html, dcc, register_page
import dash_bootstrap_components as dbc

# REGISTRAR PÁGINA FLOTA
register_page(__name__, path='/flota', name='Flota')

CNH_ROJO, CNH_OSCURO, CNH_VINO, CNH_GRIS, BLANCO = "#A4242C", "#242424", "#482024", "#A0A0A0", "#FFFFFF"

def crear_kpi_flota(titulo, valor, color_borde):
    return dbc.Card(dbc.CardBody([
        html.H6(titulo, className="text-muted text-uppercase text-center", style={"fontSize": "10px"}),
        html.H4(valor, className="fw-bold mb-0 text-center", style={"color": color_borde})
    ]), style={"borderTop": f"4px solid {color_borde}", "boxShadow": "0 2px 4px rgba(0,0,0,0.05)"})

layout = html.Div([
    html.H2("Análisis de Integridad de Flota", className="mb-4 fw-bold"),

    # SECCIÓN 1: DIAGNÓSTICO (G1 + 4 KPIs)
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody("Espacio para G1: Valores Faltantes"), style={"height": "350px"}), width=8),
        dbc.Col([
            dbc.Row([
                dbc.Col(crear_kpi_flota("Dato A", "00", CNH_OSCURO), width=6),
                dbc.Col(crear_kpi_flota("Dato B", "00", CNH_ROJO), width=6),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col(crear_kpi_flota("Dato C", "00", CNH_VINO), width=6),
                dbc.Col(crear_kpi_flota("Dato D", "00", CNH_GRIS), width=6),
            ]),
        ], width=4, className="d-flex flex-column justify-content-center")
    ], className="mb-5"),

    # SECCIÓN 2: RESPONSABLES Y GEOGRAFÍA (G2 y G3)
    dbc.Row([
        # Distribuidores
        dbc.Col([
            html.H5("Responsabilidad por Distribuidor", className="fw-bold mb-3"),
            dbc.Row([
                dbc.Col(crear_kpi_flota("KPI 1", "00", CNH_ROJO), width=6),
                dbc.Col(crear_kpi_flota("KPI 2", "00", CNH_OSCURO), width=6),
            ], className="mb-3"),
            dbc.Card(dbc.CardBody("Espacio para G2"), style={"height": "300px"})
        ], width=6),
        # Ubicación
        dbc.Col([
            html.H5("Ubicación Geográfica (Estados)", className="fw-bold mb-3"),
             dbc.Row([
                dbc.Col(crear_kpi_flota("KPI 3", "00", CNH_VINO), width=6),
                dbc.Col(crear_kpi_flota("KPI 4", "00", CNH_GRIS), width=6),
            ], className="mb-3"),
            dbc.Card(dbc.CardBody("Espacio para G3"), style={"height": "300px"})
        ], width=6),
    ], className="mb-5"),

    # SECCIÓN 3: IMPACTO OPERATIVO (G4)
    html.H5("Detalle por Unidades y Modelos", className="fw-bold mb-3"),
    dbc.Row([
        dbc.Col(crear_kpi_flota("Impacto A", "00", CNH_ROJO), width=3),
        dbc.Col(crear_kpi_flota("Impacto B", "00", CNH_OSCURO), width=3),
        dbc.Col(crear_kpi_flota("Impacto C", "00", CNH_VINO), width=3),
        dbc.Col(crear_kpi_flota("Impacto D", "00", CNH_GRIS), width=3),
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody("Espacio para G4: Unidades"), style={"height": "400px"}), width=12)
    ])
])