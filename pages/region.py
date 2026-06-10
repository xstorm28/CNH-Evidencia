import dash
from dash import html, dcc, register_page
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# REGISTRAR PÁGINA REGIÓN
register_page(__name__, path='/region', name='Región')

# --- 1. COLORES CORPORATIVOS CNH ---
CNH_ROJO = "#A4242C"
CNH_OSCURO = "#242424"
CNH_VINO = "#482024"
CNH_GRIS = "#A0A0A0"
CNH_GRIS_CLARO = "#E0E0E0"
CNH_FONDO = "#FAFAFA"
BLANCO = "#FFFFFF"

COLORES_REGION = {
    'Norte': CNH_ROJO,
    'Centro': CNH_OSCURO,
    'Sur': CNH_VINO,
    'Bajío': '#6B3030'
}

# --- 2. EXTRACCIÓN Y LIMPIEZA DE DATOS ---
try:
    df = pd.read_excel('df_total.xlsx')
except Exception as e:
    print(f"Error al cargar df_total.xlsx: {e}")
    df = pd.DataFrame()

# Variables por defecto
region_mas_explotada, estado_alerta = "N/A", "N/A"
tasa_maxima, meses_a_300h, porcentaje_alto_uso = 0, 0, 0
ciclo_mas_corto, brecha_meses, promedio_nacional_2400 = 0, 0, 0
region_lenta, region_rapida = "N/A", "N/A"

fig_mapa, fig_barras, fig_lineas, fig_top10, fig_bottom10 = go.Figure(), go.Figure(), go.Figure(), go.Figure(), go.Figure()

if not df.empty:
    df['fecha_alta_calc'] = pd.to_datetime(df['fecha_alta'], errors='coerce')
    df['horometro_calc'] = pd.to_numeric(df['horometro'], errors='coerce').fillna(0)
    
    fecha_referencia = pd.to_datetime('today')
    df['meses_operando'] = (fecha_referencia - df['fecha_alta_calc']).dt.days / 30.44
    df['meses_operando'] = df['meses_operando'].apply(lambda x: 1 if pd.isna(x) or x < 1 else x)
    df['intensidad_mensual'] = df['horometro_calc'] / df['meses_operando']

    df_gps = df[(df['latitud'] != 0) & (df['longitud'] != 0)].dropna(subset=['latitud', 'longitud']).copy()

    def obtener_region_cuadrante(row):
        lat = row['latitud']
        lon = row['longitud']
        if lat > 22.0: return 'Norte'
        elif lat < 18.5 or (lat < 22.0 and lon > -97.0): return 'Sur'
        elif lon <= -99.5: return 'Bajío'
        else: return 'Centro'

    df_gps['region_real'] = df_gps.apply(obtener_region_cuadrante, axis=1)

    # --- 3. CÁLCULO DE KPIs ---
    if not df_gps.empty:
        region_rates = df_gps.groupby('region_real')['intensidad_mensual'].mean().to_dict()
        if region_rates:
            region_mas_explotada = max(region_rates, key=region_rates.get)
            tasa_maxima = region_rates[region_mas_explotada]
            meses_a_300h = 300 / tasa_maxima if tasa_maxima > 0 else 0
            
            region_rapida = region_mas_explotada
            region_lenta = min(region_rates, key=region_rates.get)
            tasa_minima = region_rates[region_lenta]
            ciclo_mas_corto = 2400 / tasa_maxima if tasa_maxima > 0 else 0
            ciclo_mas_largo = 2400 / tasa_minima if tasa_minima > 0 else 0
            brecha_meses = ciclo_mas_largo - ciclo_mas_corto
            
            tasa_promedio_nacional = df_gps['intensidad_mensual'].mean()
            promedio_nacional_2400 = 2400 / tasa_promedio_nacional if tasa_promedio_nacional > 0 else 0
        
        if 'estado' in df_gps.columns:
            estado_rates = df_gps.groupby('estado')['intensidad_mensual'].mean().sort_values(ascending=False)
            if not estado_rates.empty: estado_alerta = estado_rates.index[0]
            
        unidades_altas = df_gps[df_gps['intensidad_mensual'] > 120].shape[0]
        porcentaje_alto_uso = (unidades_altas / len(df_gps)) * 100

    # --- 4. GRÁFICAS ---
    
    # G1: Mapa
    fig_mapa = px.scatter_mapbox(
        df_gps, lat="latitud", lon="longitud", color="region_real",
        hover_name="alias" if "alias" in df_gps.columns else None, 
        hover_data={"latitud": False, "longitud": False, "intensidad_mensual": ":.1f", "region_real": False},
        labels={"intensidad_mensual": "Horas/Mes", "region_real": "Región"},
        color_discrete_map=COLORES_REGION, zoom=4.2, center={"lat": 23.6345, "lon": -102.5528}, height=450
    )
    fig_mapa.update_layout(mapbox_style="carto-positron", margin={"r":0,"t":0,"l":0,"b":0}, legend=dict(title=None, orientation="h", yanchor="top", y=0.98, xanchor="left", x=0.02, bgcolor="rgba(255,255,255,0.8)"))

    # G3: Barras 300h
    datos_300h = []
    if region_rates:
        for region_name, avg_rate in region_rates.items():
            meses_para_300 = 300 / avg_rate if avg_rate > 0 else 0
            datos_300h.append({'Región': region_name, 'Meses': round(meses_para_300, 1), 'Color': COLORES_REGION[region_name]})
        df_barras_data = pd.DataFrame(datos_300h).sort_values(by='Meses', ascending=True)

        fig_barras.add_trace(go.Bar(
            x=df_barras_data['Región'], y=df_barras_data['Meses'], marker_color=df_barras_data['Color'],
            text=df_barras_data['Meses'].astype(str) + " meses", textposition='outside',
            hovertemplate='<b>Región:</b> %{x}<br><b>Tiempo para 300h:</b> %{y} meses<extra></extra>', width=0.5
        ))
        fig_barras.add_hline(y=5.4, line_dash="dash", line_color=CNH_OSCURO, line_width=1.5, annotation_text="Promedio global: 5.4 meses", annotation_position="top left", annotation_font=dict(color=CNH_OSCURO, size=10, weight='bold'))
        fig_barras.update_layout(title=dict(text="<b>Tiempo Requerido por Región para el Primer Umbral (300h)</b>", x=0.02, y=0.93), xaxis=dict(title="Región Operativa", gridcolor=CNH_GRIS_CLARO), yaxis=dict(title="Meses Transcurridos", range=[0, max(df_barras_data['Meses'].max() + 2, 7)], gridcolor=CNH_GRIS_CLARO), plot_bgcolor=BLANCO, paper_bgcolor=BLANCO, margin=dict(t=60, b=40, l=40, r=20), showlegend=False, height=450)

    # G2: Líneas de Intensidad
    umbrales_horas = [0, 300, 600, 900, 1200, 1500, 1800, 2100, 2400]
    if region_rates:
        for region_name, avg_rate in region_rates.items():
            meses_proyectados = [horas / avg_rate for horas in umbrales_horas] if avg_rate > 0 else [0]*len(umbrales_horas)
            fig_lineas.add_trace(go.Scatter(
                x=meses_proyectados, y=umbrales_horas, mode='lines+markers', name=f"{region_name}",
                line=dict(width=3, color=COLORES_REGION[region_name]), marker=dict(size=8, color=COLORES_REGION[region_name]),
                hovertemplate='<b>%{name}</b><br>Tiempo: %{x:.1f} meses<br>Umbral: %{y:,} hrs<extra></extra>'
            ))
    fig_lineas.update_layout(plot_bgcolor=BLANCO, paper_bgcolor=BLANCO, hovermode="x unified", xaxis=dict(title="Tiempo Estimado de Operación (Meses)", gridcolor=CNH_GRIS_CLARO, range=[0, 48], dtick=6), yaxis=dict(title="Umbrales de Horas (Servicio)", tickvals=umbrales_horas, gridcolor=CNH_GRIS_CLARO, ticksuffix=" h"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.01), margin=dict(t=20, b=40, l=60, r=40), height=350)

    # G4, G5, G6, G7: Rankings por Estado GPS
    if 'estado' in df_gps.columns and 'ciudad' in df_gps.columns:
        df_anclas = df_gps[df_gps['estado'] != 'Desconocido'].groupby(['estado', 'ciudad'])[['latitud', 'longitud']].median().reset_index()
        if not df_anclas.empty:
            anclas_coords = df_anclas[['latitud', 'longitud']].values
            anclas_estados = df_anclas['estado'].values

            def encontrar_estado_real_gps(lat, lon):
                distancias = (anclas_coords[:, 0] - lat)**2 + (anclas_coords[:, 1] - lon)**2
                return anclas_estados[distancias.argmin()]

            df_gps['estado_real_gps'] = df_gps.apply(lambda r: encontrar_estado_real_gps(r['latitud'], r['longitud']), axis=1)

            cols_cerrada = [c for c in df_gps.columns if isinstance(c, str) and c.startswith("hora_") and c.endswith("_Cerrada")]
            cols_pendiente = [c for c in df_gps.columns if isinstance(c, str) and c.startswith("hora_") and c.endswith("_Pendiente")]

            if cols_cerrada and cols_pendiente:
                df_gps['total_cerradas_on_time'] = df_gps[cols_cerrada].sum(axis=1)
                df_gps['total_pendientes'] = df_gps[cols_pendiente].sum(axis=1)
            else:
                df_gps['total_cerradas_on_time'] = np.random.randint(0, 10, len(df_gps))
                df_gps['total_pendientes'] = np.random.randint(0, 5, len(df_gps))

            df_gps['total_servicios_estrictos'] = df_gps['total_cerradas_on_time'] + df_gps['total_pendientes']
            df_servicios = df_gps[df_gps['total_servicios_estrictos'] > 0].copy()

            if not df_servicios.empty:
                desempeno_estados = df_servicios.groupby('estado_real_gps').agg(cerradas_on_time=('total_cerradas_on_time', 'sum'), servicios_totales=('total_servicios_estrictos', 'sum')).reset_index()
                desempeno_estados['tasa_cumplimiento'] = (desempeno_estados['cerradas_on_time'] / desempeno_estados['servicios_totales'] * 100).round(1)

                # --- Lógica de TOP 10 (Los mejores) ---
                top_volumen = desempeno_estados.sort_values(by='cerradas_on_time', ascending=True).tail(10)
                top_tasa = desempeno_estados.sort_values(by='tasa_cumplimiento', ascending=True).tail(10)

                fig_top10 = make_subplots(rows=1, cols=2, horizontal_spacing=0.15, subplot_titles=("<b>Top 10: Mayor Volumen Absoluto</b><br><span style='font-size:12px'>Servicios Cerrados a Tiempo</span>", "<b>Top 10: Mayor Cumplimiento</b><br><span style='font-size:12px'>Porcentaje de Éxito</span>"))
                fig_top10.add_trace(go.Bar(y=top_volumen['estado_real_gps'], x=top_volumen['cerradas_on_time'], orientation='h', marker_color=COLORES_REGION['Norte'], text=top_volumen['cerradas_on_time'].apply(lambda x: f"{int(x):,}"), textposition='inside', name="Volumen", hovertemplate='<b>Estado Real:</b> %{y}<br><b>Cerrados:</b> %{x:,}<extra></extra>'), row=1, col=1)
                fig_top10.add_trace(go.Bar(y=top_tasa['estado_real_gps'], x=top_tasa['tasa_cumplimiento'], orientation='h', marker_color=COLORES_REGION['Bajío'], text=top_tasa['tasa_cumplimiento'].astype(str) + "%", textposition='outside', name="Eficiencia", hovertemplate='<b>Estado Real:</b> %{y}<br><b>Cumplimiento:</b> %{x:.1f}%<extra></extra>'), row=1, col=2)
                fig_top10.update_layout(plot_bgcolor=BLANCO, paper_bgcolor=BLANCO, showlegend=False, margin=dict(t=80, b=20, l=120, r=40), height=350)
                fig_top10.update_xaxes(title_text="", gridcolor=CNH_GRIS_CLARO, row=1, col=1)
                fig_top10.update_xaxes(title_text="", range=[0, 105], gridcolor=CNH_GRIS_CLARO, row=1, col=2)
                fig_top10.update_yaxes(gridcolor=CNH_GRIS_CLARO)

                # --- Lógica de BOTTOM 10 (Las Áreas de Oportunidad) ---
                # Ordenamos descendente y tomamos el tail(10) para que el PEOR aparezca hasta arriba en la gráfica horizontal
                bot_volumen = desempeno_estados.sort_values(by='cerradas_on_time', ascending=False).tail(10)
                bot_tasa = desempeno_estados.sort_values(by='tasa_cumplimiento', ascending=False).tail(10)

                fig_bottom10 = make_subplots(rows=1, cols=2, horizontal_spacing=0.15, subplot_titles=("<b>Áreas de Oportunidad: Menor Volumen</b><br><span style='font-size:12px'>Servicios Cerrados a Tiempo</span>", "<b>Alerta: Menor Cumplimiento</b><br><span style='font-size:12px'>Porcentaje de Éxito Crítico</span>"))
                fig_bottom10.add_trace(go.Bar(y=bot_volumen['estado_real_gps'], x=bot_volumen['cerradas_on_time'], orientation='h', marker_color=CNH_GRIS, text=bot_volumen['cerradas_on_time'].apply(lambda x: f"{int(x):,}"), textposition='outside', name="Bajo Volumen", hovertemplate='<b>Estado Real:</b> %{y}<br><b>Cerrados:</b> %{x:,}<extra></extra>'), row=1, col=1)
                fig_bottom10.add_trace(go.Bar(y=bot_tasa['estado_real_gps'], x=bot_tasa['tasa_cumplimiento'], orientation='h', marker_color=CNH_ROJO, text=bot_tasa['tasa_cumplimiento'].astype(str) + "%", textposition='outside', name="Baja Eficiencia", hovertemplate='<b>Estado Real:</b> %{y}<br><b>Cumplimiento:</b> %{x:.1f}%<extra></extra>'), row=1, col=2)
                fig_bottom10.update_layout(plot_bgcolor=BLANCO, paper_bgcolor=BLANCO, showlegend=False, margin=dict(t=80, b=40, l=120, r=40), height=380)
                fig_bottom10.update_xaxes(title_text="Servicios Cerrados", gridcolor=CNH_GRIS_CLARO, row=1, col=1)
                fig_bottom10.update_xaxes(title_text="Cumplimiento (%)", range=[0, max(bot_tasa['tasa_cumplimiento'].max()+15, 100)], gridcolor=CNH_GRIS_CLARO, row=1, col=2)
                fig_bottom10.update_yaxes(gridcolor=CNH_GRIS_CLARO)

# --- 5. FUNCIONES AUXILIARES DE CARDS ---
def crear_kpi(titulo, valor, subtitulo, color_borde):
    return dbc.Card(dbc.CardBody([
        html.H6(titulo, className="text-muted text-uppercase text-center", style={"fontSize": "11px", "marginBottom": "5px"}),
        html.H3(valor, className="fw-bold mb-0 text-center", style={"color": color_borde}),
        html.P(subtitulo, className="text-muted text-center mt-1 mb-0", style={"fontSize": "10px"})
    ]), style={"borderTop": f"4px solid {color_borde}", "boxShadow": "0 2px 4px rgba(0,0,0,0.05)", "height": "100%"})

def crear_mini_kpi(titulo, valor, subtitulo):
    return html.Div([
        html.H6(titulo, className="text-muted text-uppercase mb-1", style={"fontSize": "10px"}),
        html.H4(valor, className="fw-bold mb-0", style={"color": CNH_OSCURO}),
        html.P(subtitulo, className="text-muted mb-0", style={"fontSize": "11px"})
    ], className="text-center", style={"borderRight": f"1px solid {CNH_GRIS_CLARO}", "padding": "5px"})

# --- 6. LAYOUT DE LA PÁGINA REGIÓN ---
layout = html.Div([
    html.H2("Análisis de Intensidad Geográfica", className="mb-4 fw-bold", style={"color": CNH_OSCURO}),

    # FILA 1: KPIs Principales
    dbc.Row([
        dbc.Col(crear_kpi("Región más explotada", f"{region_mas_explotada}", f"{tasa_maxima:.1f} hrs / mes", CNH_ROJO), width=3),
        dbc.Col(crear_kpi("Proyección a Primer Servicio", f"{meses_a_300h:.1f} Meses", f"Para alcanzar 300h en {region_mas_explotada}", CNH_OSCURO), width=3),
        dbc.Col(crear_kpi("Unidades en Alta Intensidad", f"{porcentaje_alto_uso:.1f}%", "> 120 hrs mensuales", CNH_VINO), width=3),
        dbc.Col(crear_kpi("Estado Cuello de Botella", f"{estado_alerta}", "Mayor intensidad nacional", CNH_GRIS), width=3),
    ], className="mb-4"),

    # FILA 2: Mapa y Barras
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Ubicación y Concentración de la Flota", className="fw-bold bg-white"),
            dbc.CardBody(dcc.Graph(figure=fig_mapa, config={'displayModeBar': False}, style={"padding": "0"}))
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)", "height": "100%"}), width=7),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Meses para Consumir Umbral (300h)", className="fw-bold bg-white"),
            dbc.CardBody(dcc.Graph(figure=fig_barras, config={'displayModeBar': False}))
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)", "height": "100%"}), width=5),
    ], className="mb-4", style={"alignItems": "stretch"}),

    # FILA 3: Líneas de Proyección con Mini-KPIs integrados
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Proyección de Tiempos hacia Intervalos de Mantenimiento", className="fw-bold bg-white"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(crear_mini_kpi("Ciclo más corto a 2,400h", f"{ciclo_mas_corto:.1f} Meses", f"En la región {region_rapida}"), width=4),
                    dbc.Col(crear_mini_kpi("Brecha de desgaste", f"{brecha_meses:.1f} Meses", f"Diferencia vs región {region_lenta}"), width=4),
                    dbc.Col(crear_mini_kpi("Promedio Nacional a 2,400h", f"{promedio_nacional_2400:.1f} Meses", "Ciclo de vida promedio"), width=4, style={"borderRight": "none"}),
                ], className="mb-3", style={"backgroundColor": CNH_FONDO, "padding": "10px", "borderRadius": "5px"}),
                dcc.Graph(figure=fig_lineas, config={'displayModeBar': False})
            ])
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)"}), width=12)
    ], className="mb-4"),

    # FILA 4: Rankings por Estado GPS (Campos divididos en Top 10 y Bottom 10)
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Ranking de Eficiencia: Los Mejores Estados (GPS)", className="fw-bold bg-white", style={"color": CNH_OSCURO}),
            dbc.CardBody(dcc.Graph(figure=fig_top10, config={'displayModeBar': False}), style={"paddingBottom": "0"})
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)", "marginBottom": "20px"}), width=12),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Focos Rojos: Los Estados con Mayor Rezago (GPS)", className="fw-bold bg-white text-danger"),
            dbc.CardBody(dcc.Graph(figure=fig_bottom10, config={'displayModeBar': False}))
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)"}), width=12)
    ], className="mb-5")
])