import dash
import dash_bootstrap_components as dbc
from dash import html, dcc

# 1. Inicialización con Multipage habilitado
app = dash.Dash(
    __name__, 
    use_pages=True, # ACTIVAR MÚLTIPLES PÁGINAS
    external_stylesheets=[dbc.themes.LUX],
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

# --- COLORES CNH ---
CNH_OSCURO = "#242424"
CNH_ROJO = "#A4242C"

# --- ESTILO SIDEBAR ---
SIDEBAR_STYLE = {
    "position": "fixed", "top": 0, "left": 0, "bottom": 0,
    "width": "16rem", "padding": "2rem 1rem", "background-color": CNH_OSCURO,
}

CONTENT_STYLE = {
    "margin-left": "18rem", "margin-right": "2rem", "padding": "2rem 1rem",
    "minHeight": "100vh"
}

# --- NAVEGACIÓN DINÁMICA ---
# Ahora el sidebar lee automáticamente las páginas que registremos
sidebar = html.Div([
    html.Div(html.Img(src="/assets/logo.png", style={"width": "100%", "maxWidth": "150px"}), className="text-center mb-4"),
    html.Hr(style={"borderColor": CNH_ROJO}),
    dbc.Nav(
        [
            dbc.NavLink(page["name"], href=page["relative_path"], active="exact")
            for page in dash.page_registry.values()
        ],
        vertical=True, pills=True,
    ),
], style=SIDEBAR_STYLE)

# --- LAYOUT PRINCIPAL ---
app.layout = html.Div([
    sidebar,
    html.Div(dash.page_container, style=CONTENT_STYLE) # Aquí se cargará cada página
])

if __name__ == "__main__":
    app.run(debug=True)