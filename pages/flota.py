import dash
from dash import html, dcc, register_page
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import missingno as msno
import matplotlib.pyplot as plt
import io
import base64

# REGISTRAR PÁGINA FLOTA
register_page(__name__, path='/flota', name='Flota')

# --- COLORES CNH ---
CNH_ROJO = "#A4242C"
CNH_OSCURO = "#242424"
CNH_VINO = "#482024"
CNH_GRIS = "#A0A0A0"
CNH_GRIS_CLARO = "#E0E0E0"
CNH_FONDO = "#FAFAFA"
BLANCO = "#FFFFFF"

# --- 1. DATOS Y CÁLCULOS REALES ---
try:
    df_flota = pd.read_excel('flota.xlsx')
except Exception as e:
    print(f"Error al cargar el archivo: {e}")
    df_flota = pd.DataFrame()

# --- 2. PROCESAMIENTO MÈTRICAS E INSIGHTS ---
HORAS = ['hora_300','hora_600','hora_900','hora_1200','hora_1500','hora_1800','hora_2100','hora_2400']
columnas_presentes = [col for col in HORAS if col in df_flota.columns]

total_flota, total_dark, pct_dark_glob, dist_critico = 0, 0, 0, "N/A"
herencia_dark, pct_herencia_sobre_dark = 0, 0
top8 = pd.DataFrame()
comp_estado = pd.DataFrame()
top_mod = pd.DataFrame()

if not df_flota.empty and columnas_presentes:
    df_flota['nan_count'] = df_flota[columnas_presentes].isnull().sum(axis=1)
    df_flota['completo']  = df_flota['nan_count'] == 0
    df_flota['dark']      = ~df_flota['completo']
    
    total_flota   = len(df_flota)
    total_dark    = df_flota['dark'].sum()
    pct_dark_glob = (total_dark / total_flota) * 100 if total_flota > 0 else 0

    # Lógica Distribuidor (G2)
    if 'distribuidor' in df_flota.columns:
        comp_dist = (df_flota.groupby('distribuidor')
                       .agg(total=('completo','count'), completos=('completo','sum'))
                       .reset_index())
        comp_dist['dark_abs']   = comp_dist['total'] - comp_dist['completos']
        comp_dist['tasa_dark']  = (comp_dist['dark_abs'] / comp_dist['total']) * 100
        comp_dist['tasa_comp']  = (comp_dist['completos'] / comp_dist['total']) * 100
        top8 = comp_dist[comp_dist['total'] >= 30].sort_values('dark_abs', ascending=False).head(8)
        dist_critico  = top8.iloc[0]['distribuidor'] if not top8.empty else "N/A"

   # Lógica Geográfica filtrada al Top 3 de Distribuidores (G3)
    if 'estado' in df_flota.columns and 'latitud' in df_flota.columns and 'longitud' in df_flota.columns and not top8.empty:
        top3_nombres = top8['distribuidor'].head(3).tolist()
        df_top3 = df_flota[df_flota['distribuidor'].isin(top3_nombres)].copy()

        # AQUÍ LA NUEVA LOGICA: Marcamos cuáles equipos son HERENCIA en el Top 3 antes de agrupar
        df_top3['es_herencia'] = df_top3['modelo'].astype(str).str.contains('HERENCIA', na=False)

        # Agrupamos agregando la suma de cuántos equipos son HERENCIA
        comp_estado = (df_top3.groupby(['estado', 'distribuidor'])
                         .agg(total=('completo','count'), 
                              completos=('completo','sum'),
                              herencia_total=('es_herencia', 'sum'), # Nueva suma
                              lat=('latitud', 'mean'), 
                              lon=('longitud', 'mean'))
                         .reset_index())
        comp_estado['dark_abs']  = comp_estado['total'] - comp_estado['completos']
        comp_estado = comp_estado[comp_estado['lat'].notna() & comp_estado['lon'].notna() & (comp_estado['dark_abs'] > 0)]

    # Lógica Modelos y Familia HERENCIA (G4)
    if 'modelo' in df_flota.columns:
        mod_stats = (df_flota.groupby('modelo')
                       .agg(total=('dark','count'), dark_abs=('dark','sum'))
                       .reset_index())
        mod_stats['tasa_dark'] = mod_stats['dark_abs'] / mod_stats['total'] * 100
        mod_stats['es_herencia'] = mod_stats['modelo'].astype(str).str.contains('HERENCIA', na=False)
        top_mod = mod_stats.sort_values('dark_abs', ascending=False).head(12)

        herencia_dark  = df_flota[(df_flota['modelo'].astype(str).str.contains('HERENCIA', na=False)) & df_flota['dark']].shape[0]
        pct_herencia_sobre_dark = (herencia_dark / total_dark * 100) if total_dark > 0 else 0

# --- 3. GENERACIÓN EN TIEMPO REAL DE MISSINGNO ---
if not df_flota.empty:
    fig_msno = plt.figure(figsize=(10, 4))
    ax = fig_msno.add_subplot(111)
    cnh_rojo_rgb = (0.64, 0.14, 0.17)
    msno.matrix(df_flota, color=cnh_rojo_rgb, sparkline=False, ax=ax, fontsize=10)
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', facecolor='#FFFFFF', dpi=100)
    plt.close(fig_msno)
    buf.seek(0)
    encoded_image = base64.b64encode(buf.read()).decode("ascii")
    src_missingno = f"data:image/png;base64,{encoded_image}"
else:
    src_missingno = ""

# --- 4. GRÁFICAS (G2, G3, G4) ---
# G2: Barras Apiladas por Distribuidor
fig_g2 = go.Figure()
if not top8.empty:
    tooltip_g2 = [
        f"<b>{row.distribuidor}</b><br>Equipos totales: {row.total:,}<br>"
        f"Dark data: <b>{row.dark_abs:,} ({row.tasa_dark:.1f}%)</b><br>"
        f"Con registro completo: {row.completos:,} ({row.tasa_comp:.1f}%)"
        for _, row in top8.iterrows()
    ]
    fig_g2.add_trace(go.Bar(y=top8['distribuidor'], x=top8['dark_abs'], orientation='h', name='Sin trazabilidad', marker_color=CNH_ROJO, marker_line_color=CNH_OSCURO, marker_line_width=0.8, hovertext=tooltip_g2, hoverinfo='text', hoverlabel=dict(bgcolor=BLANCO, bordercolor=CNH_ROJO)))
    fig_g2.add_trace(go.Bar(y=top8['distribuidor'], x=top8['completos'], orientation='h', name='Registro completo', marker_color=CNH_GRIS_CLARO, marker_line_color=CNH_GRIS, marker_line_width=0.8, hoverinfo='skip'))
    fig_g2.update_layout(barmode='stack', plot_bgcolor=CNH_FONDO, paper_bgcolor=BLANCO, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), xaxis=dict(title="Número de equipos", gridcolor=CNH_GRIS_CLARO, gridwidth=0.5), yaxis=dict(showgrid=False, autorange="reversed"), height=350, margin=dict(t=40, b=40, l=160, r=20), hovermode="closest")

# G3: Mapa de Burbujas
fig_g3 = go.Figure()
if not comp_estado.empty:
    colores_top3 = [CNH_ROJO, CNH_OSCURO, CNH_VINO]
    max_dark = comp_estado['dark_abs'].max()
    sizeref_calc = 2 * max_dark / (35**2) if max_dark > 0 else 1

    for idx, dist_nombre in enumerate(top3_nombres):
        df_sub = comp_estado[comp_estado['distribuidor'] == dist_nombre]
        if df_sub.empty: continue
        
        fig_g3.add_trace(go.Scattergeo(
            lon=df_sub['lon'], lat=df_sub['lat'], text=df_sub['estado'], name=dist_nombre,
            marker=dict(size=df_sub['dark_abs'], sizemode='area', sizeref=sizeref_calc, color=colores_top3[idx % 3], line=dict(color=BLANCO, width=1), opacity=0.85),
            # Actualizamos el hovertemplate para incluir las unidades HERENCIA
            hovertemplate="<b>" + dist_nombre + "</b><br>"
                          "Estado: %{text}<br>"
                          "Equipos totales: %{customdata[0]:,}<br>"
                          "└─ de los cuales HERENCIA: <b>%{customdata[2]:,}</b><br>" # Línea nueva
                          "Dark data: <span style='color:#A4242C'><b>%{customdata[1]:,}</b></span> equipos<extra></extra>",
            # Añadimos 'herencia_total' en la posición 2 del arreglo (índice 2 de customdata)
            customdata=np.stack((df_sub['total'], df_sub['dark_abs'], df_sub['herencia_total']), axis=-1)
        ))

fig_g3.update_layout(
    geo=dict(scope='north america', showland=True, landcolor="#F4F4F4", subunitcolor=BLANCO, countrycolor=CNH_GRIS, showlakes=False, projection_type='mercator', center=dict(lat=23.6345, lon=-102.5528), lonaxis=dict(range=[-118, -86]), lataxis=dict(range=[14, 33])),
    paper_bgcolor=BLANCO, margin=dict(t=10, b=10, l=10, r=10), height=350, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5)
)

# G4: Modelos (Familia HERENCIA)
fig_g4 = go.Figure()
if not top_mod.empty:
    colores_mod = [CNH_ROJO if h else CNH_GRIS_CLARO for h in top_mod['es_herencia']]
    tooltip_g4 = [
        f"<b>{row.modelo}</b><br>Equipos con dark data: <b>{row.dark_abs:,}</b><br>Tasa dark data: {row.tasa_dark:.1f}%<br>Total equipos: {row.total:,}" + ("<br><b>⚠ Familia HERENCIA</b>" if row.es_herencia else "")
        for _, row in top_mod.iterrows()
    ]
    fig_g4.add_trace(go.Bar(
        x=top_mod['modelo'], y=top_mod['dark_abs'], marker_color=colores_mod, marker_line_color=CNH_OSCURO, marker_line_width=0.8,
        text=[f"{int(v):,}" for v in top_mod['dark_abs']], textposition='outside', textfont=dict(size=10, color=CNH_OSCURO, family="Arial Black"),
        hovertext=tooltip_g4, hoverinfo='text', hoverlabel=dict(bgcolor=BLANCO, bordercolor=CNH_ROJO)
    ))
    fig_g4.update_layout(
        plot_bgcolor=CNH_FONDO, paper_bgcolor=BLANCO, xaxis=dict(showgrid=False, tickangle=-30), yaxis=dict(title="Equipos con dark data", gridcolor=CNH_GRIS_CLARO, gridwidth=0.5),
        height=400, margin=dict(t=30, b=80, l=60, r=40), hovermode="closest",
    )

# --- 5. FUNCIONES AUXILIARES DE CARDS ---
def crear_kpi_flota(titulo, valor, color_borde):
    return dbc.Card(dbc.CardBody([
        html.H6(titulo, className="text-muted text-uppercase text-center", style={"fontSize": "11px", "minHeight": "28px"}),
        html.H4(valor, className="fw-bold mb-0 text-center", style={"color": color_borde})
    ]), style={"borderTop": f"4px solid {color_borde}", "boxShadow": "0 2px 4px rgba(0,0,0,0.05)", "height": "100%"})

# --- 6. LAYOUT DE LA PÁGINA FLOTA ---
layout = html.Div([
    html.H2("Análisis de Integridad de Flota", className="mb-4 fw-bold", style={"color": CNH_OSCURO}),

    # SECCIÓN 1: DIAGNÓSTICO
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Matriz de Integridad de Datos (Valores Faltantes)", className="fw-bold bg-white"),
                dbc.CardBody(html.Img(src=src_missingno, style={"width": "100%", "borderRadius": "4px"}) if src_missingno else html.P("No hay datos"))
            ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)", "height": "100%"}), 
            width=8
        ),
        dbc.Col([
            dbc.Row([
                dbc.Col(crear_kpi_flota("Dark data global", f"{'45.4'}%", CNH_ROJO), width=6),
                dbc.Col(crear_kpi_flota("Equipos sin registros", f"{total_dark:,}", CNH_VINO), width=6),
            ], className="mb-3", style={"height": "47%"}),
            dbc.Row([
                dbc.Col(crear_kpi_flota("Total en reporte", f"{total_flota:,}", CNH_GRIS), width=6),
                dbc.Col(crear_kpi_flota("Distribuidor Crítico", dist_critico, CNH_OSCURO), width=6),
            ], style={"height": "47%"}),
        ], width=4, className="d-flex flex-column justify-content-between")
    ], className="mb-5 align-items-stretch"),

    # SECCIÓN 2: RESPONSABLES Y GEOGRAFÍA
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Distribución de Dark Data por Distribuidor (Top 8)", className="fw-bold bg-white"),
                dbc.CardBody(dcc.Graph(figure=fig_g2, config={'displayModeBar': False}))
            ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)", "height": "100%"})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Ubicación Geográfica de los 3 Distribuidores Críticos", className="fw-bold bg-white"),
                dbc.CardBody(dcc.Graph(figure=fig_g3, config={'displayModeBar': False}))
            ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)", "height": "100%"})
        ], width=6),
    ], className="mb-5", style={"alignItems": "stretch"}),

    # SECCIÓN 3: IMPACTO OPERATIVO Y MODELOS HERENCIA
    html.H5("Detalle por Familias y Modelos", className="fw-bold mb-3", style={"color": CNH_OSCURO}),
    dbc.Row([
        dbc.Col(crear_kpi_flota("Equipos HERENCIA en Dark Data", f"{int(herencia_dark):,}", CNH_ROJO), width=4),
        dbc.Col(crear_kpi_flota("% Dark Data que es HERENCIA", f"{pct_herencia_sobre_dark:.1f}%", CNH_VINO), width=4),
        dbc.Col(crear_kpi_flota("Meta 6 meses (Rescate)", "2,500", CNH_GRIS), width=4),
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Los modelos de la familia HERENCIA (barras rojas) concentran la mayoría de los equipos sin trazabilidad", className="fw-bold bg-white"),
            dbc.CardBody(dcc.Graph(figure=fig_g4, config={'displayModeBar': False}))
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)"}), width=12)
    ], className="mb-5")
])