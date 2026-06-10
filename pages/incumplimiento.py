import dash
from dash import html, dcc, register_page, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# REGISTRAR PÁGINA INCUMPLIMIENTO
register_page(__name__, path='/incumplimiento', name='Incumplimiento', order=4)

# --- 1. COLORES CORPORATIVOS Y DICCIONARIOS ---
CNH_ROJO = "#A4242C"
CNH_OSCURO = "#242424"
CNH_VINO = "#482024"
CNH_GRIS = "#A0A0A0"
CNH_GRIS_CLARO = "#E0E0E0"
CNH_FONDO = "#FAFAFA"
BLANCO = "#FFFFFF"

UMBRALES = [300, 600, 900, 1200, 1500, 1800, 2100, 2400]
UMBRAL_LABELS = [f'{u}h' for u in UMBRALES]

COLORES_UMBRAL = {
    300: '#A4242C', 600: '#A82024', 900: '#242424', 1200: '#6B3030',
    1500: '#9E9E9E', 1800: '#D4D0D0', 2100: '#888780', 2400: '#791F1F',
}

COLORES_PRIORIDAD = {
    'URGENTE'   : '#E24B4A',
    'PRÓXIMO'   : '#EF9F27',
    'Planificar': '#639922',
}

def estilo_base(fig, titulo):
    fig.update_layout(
        title       = dict(text=titulo, font=dict(size=14), x=0.02),
        font        = dict(family="Inter, Arial, sans-serif", color="#1A1A2E"),
        plot_bgcolor= '#FFFFFF', paper_bgcolor='#FFFFFF',
        margin      = dict(l=60, r=40, t=60, b=40),
        legend      = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False, linecolor="#CCCCCC")
    fig.update_yaxes(gridcolor="#F0F0F0", linecolor="#CCCCCC")
    return fig

# --- 2. EXTRACCIÓN Y PREPROCESAMIENTO DE DATOS ---
try:
    df_total = pd.read_excel('df_total.xlsx')
except Exception as e:
    print(f"Error al cargar df_total.xlsx: {e}")
    df_total = pd.DataFrame()

df_fecha = pd.DataFrame()
opciones_dropdown = [{'label': 'Sin Datos', 'value': 'Todas'}]

if not df_total.empty:
    def extraer_familia(modelo):
        if pd.isna(modelo) or modelo == 'Desconocido': return 'Otros'
        modelo = str(modelo).strip()
        if 'HERENCIA' in modelo: return 'HERENCIA'
        if modelo.startswith('TS6'): return 'TS6'
        if 'FARMALL' in modelo: return 'FARMALL'
        if modelo.startswith('6810') or modelo.startswith('7810'): return 'Serie 800'
        if modelo.startswith('TT'): return 'TT'
        if modelo.startswith('95') or modelo.startswith('B80'): return 'Serie 95/B80'
        return 'Otros'

    df_total['modelo_calc'] = df_total['Modelo'] if 'Modelo' in df_total.columns else df_total.get('modelo', 'Otros')
    df_total['familia'] = df_total['modelo_calc'].apply(extraer_familia)
    df_total['distribuidor_calc'] = df_total.get('Distribuidor', df_total.get('distribuidor', 'Desconocido'))

    # LÓGICA PREDICTIVA (30 DÍAS)
    HOY = pd.Timestamp.today()
    df_total["fecha_alta_calc"] = pd.to_datetime(df_total["Fecha Alta"] if "Fecha Alta" in df_total.columns else df_total.get("fecha_alta"), errors="coerce")
    df_total["horometro_calc"] = pd.to_numeric(df_total["Horometro"] if "Horometro" in df_total.columns else df_total.get("horometro"), errors="coerce").fillna(0)
    df_total["intensidad_mensual_calc"] = pd.to_numeric(df_total.get("intensidad_mensual", 0), errors="coerce").fillna(0)

    df_total["dias_en_uso"] = (HOY - df_total["fecha_alta_calc"]).dt.days
    df_total["slope_horas_por_dia"] = df_total["horometro_calc"] / df_total["dias_en_uso"]

    mask_sin_fecha = df_total["fecha_alta_calc"].isna() | (df_total["dias_en_uso"] <= 0)
    df_total.loc[mask_sin_fecha, "slope_horas_por_dia"] = df_total.loc[mask_sin_fecha, "intensidad_mensual_calc"] / 26
    df_total = df_total[df_total["slope_horas_por_dia"].between(0.1, 10)].copy()

    VENTANA_DIAS = 30
    df_total["horometro_proyectado"] = df_total["horometro_calc"] + df_total["slope_horas_por_dia"] * VENTANA_DIAS

    def umbral_alcanzado(row):
        for u in UMBRALES:
            if row["horometro_calc"] < u <= row["horometro_proyectado"]:
                return u
        return None

    df_total["umbral_proximo"] = df_total.apply(umbral_alcanzado, axis=1)

    def dias_para_umbral(row):
        if pd.isna(row["umbral_proximo"]): return None
        horas_faltantes = row["umbral_proximo"] - row["horometro_calc"]
        return round(horas_faltantes / row["slope_horas_por_dia"], 1)

    df_total["dias_para_umbral"] = df_total.apply(dias_para_umbral, axis=1)

    # Prioridad
    df_total['prioridad'] = 'Planificar'
    df_total.loc[df_total['dias_para_umbral'] <= 7,  'prioridad'] = 'URGENTE'
    df_total.loc[df_total['dias_para_umbral'] <= 15, 'prioridad'] = df_total.loc[df_total['dias_para_umbral'] <= 15, 'prioridad'].replace('Planificar', 'PRÓXIMO')

    # LÓGICA HISTÓRICA (Para la gráfica de Líneas)
    df_total['fecha_hist'] = pd.to_datetime(df_total.get('fecha'), errors='coerce')
    df_base_fecha = df_total.dropna(subset=["fecha_hist"]).copy()
    
    ciclo_map = {1: "Siembra O-I", 2: "Siembra O-I", 3: "Transicion", 4: "Siembra P-V", 5: "Siembra P-V", 6: "Siembra P-V", 7: "Reposo", 8: "Reposo", 9: "Cosecha P-V", 10: "Transicion", 11: "Transicion", 12: "Siembra O-I"}
    df_base_fecha["mes"] = df_base_fecha["fecha_hist"].dt.month
    df_base_fecha["ciclo"] = df_base_fecha["mes"].map(ciclo_map)

    cols_pendiente = [c for c in df_base_fecha.columns if isinstance(c, str) and c.startswith("hora_") and c.endswith("_Pendiente")]
    cols_cerrada   = [c for c in df_base_fecha.columns if isinstance(c, str) and c.startswith("hora_") and c.endswith("_Cerrada")]

    df_base_fecha["total_pendientes"] = df_base_fecha[cols_pendiente].sum(axis=1)
    df_base_fecha["total_cerradas"]   = df_base_fecha[cols_cerrada].sum(axis=1)
    df_base_fecha["total_servicios"]  = df_base_fecha["total_pendientes"] + df_base_fecha["total_cerradas"]
    
    df_fecha = df_base_fecha[df_base_fecha["total_servicios"] > 0].copy()
    df_fecha["tasa_incumplimiento"] = (df_fecha["total_pendientes"] / df_fecha["total_servicios"]) * 100

    opciones_dropdown = [{'label': 'Todas las Familias', 'value': 'Todas'}] + \
                        [{'label': str(f), 'value': str(f)} for f in sorted(df_total['familia'].unique()) if pd.notna(f)]

# --- 3. FUNCIONES AUXILIARES DE CARDS ---
def crear_kpi(titulo, valor, subtitulo, color_borde):
    return dbc.Card(dbc.CardBody([
        html.H6(titulo, className="text-muted text-uppercase text-center", style={"fontSize": "11px", "marginBottom": "5px"}),
        html.H3(valor, className="fw-bold mb-0 text-center", style={"color": color_borde}),
        html.P(subtitulo, className="text-muted text-center mt-1 mb-0", style={"fontSize": "10px"})
    ]), style={"borderTop": f"4px solid {color_borde}", "boxShadow": "0 2px 4px rgba(0,0,0,0.05)", "height": "100%"})

# --- 4. LAYOUT ---
layout = html.Div([
    dbc.Row([
        dbc.Col(html.H2("Ventana Crítica Predictiva (30 Días) y Riesgo Estructural", className="fw-bold", style={"color": CNH_OSCURO}), width=8),
        dbc.Col([
            html.Label("Filtrar por Familia de Equipo:", className="fw-bold text-muted small mb-1"),
            dcc.Dropdown(id='dropdown-familia-inc', options=opciones_dropdown, value='Todas', clearable=False, style={"boxShadow": "0 2px 4px rgba(0,0,0,0.05)"})
        ], width=4, className="d-flex flex-column justify-content-end")
    ], className="mb-4 align-items-center"),

    # FILA 1: KPIs
    dbc.Row([
        dbc.Col(id='kpi-tasa', width=3),
        dbc.Col(id='kpi-ventana', width=3),
        dbc.Col(id='kpi-pendientes', width=3),
        dbc.Col(id='kpi-estatus', width=3),
    ], className="mb-4"),

    # FILA 2: GRÁFICAS PRINCIPALES
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Proyección: Unidades en Ventana Crítica de 30 Días por Umbral", className="fw-bold bg-white"),
            dbc.CardBody(dcc.Graph(id='grafica-barras', config={'displayModeBar': False}, style={"height": "350px"}))
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)"}), width=6),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Contexto Histórico: Incumplimiento por Ciclo Agrícola", className="fw-bold bg-white"),
            dbc.CardBody(dcc.Graph(id='grafica-lineas', config={'displayModeBar': False}, style={"height": "350px"}))
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)"}), width=6),
    ], className="mb-4", style={"alignItems": "stretch"}),

    # FILA 3: EL QUIÉN Y EL QUÉ (NUEVO ENFOQUE PREDICTIVO)
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Top 10 Distribuidores con Mayor Volumen Proyectado (<30 Días)", className="fw-bold bg-white text-danger"),
            dbc.CardBody(dcc.Graph(id='grafica-distribuidores-predictiva', config={'displayModeBar': False}, style={"height": "350px"}))
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)"}), width=8),
        
        dbc.Col(dbc.Card([
            dbc.CardHeader("Nivel de Urgencia (Próximos 30 Días)", className="fw-bold bg-white"),
            dbc.CardBody(dcc.Graph(id='grafica-dona-prioridad', config={'displayModeBar': False}, style={"height": "350px"}))
        ], style={"boxShadow": "0 4px 15px rgba(0,0,0,0.1)"}), width=4),
    ], className="mb-5", style={"alignItems": "stretch"})
])

# --- 5. CALLBACK INTERACTIVO ---
@callback(
    [Output('kpi-tasa', 'children'), Output('kpi-ventana', 'children'),
     Output('kpi-pendientes', 'children'), Output('kpi-estatus', 'children'),
     Output('grafica-barras', 'figure'), Output('grafica-lineas', 'figure'),
     Output('grafica-distribuidores-predictiva', 'figure'), Output('grafica-dona-prioridad', 'figure')],
    [Input('dropdown-familia-inc', 'value')]
)
def actualizar_panel(familia_seleccionada):
    empty = go.Figure().update_layout(title="Sin datos disponibles")
    if df_total.empty:
        return [""]*4 + [empty, empty, empty, empty]

    if familia_seleccionada == 'Todas':
        df_f1 = df_total
        df_f2 = df_fecha
        titulo_fam = "Todas las Familias"
    else:
        df_f1 = df_total[df_total['familia'] == familia_seleccionada]
        df_f2 = df_fecha[df_fecha['familia'] == familia_seleccionada]
        titulo_fam = familia_seleccionada

    # Universo puramente predictivo: equipos que caen en ventana en los próximos 30 días
    en_ventana = df_f1[df_f1["umbral_proximo"].notna()].copy()
    unidades_criticas = len(en_ventana)

    tasa_promedio = df_f2['tasa_incumplimiento'].mean() if not df_f2.empty else 0
    total_pend = df_f2['total_pendientes'].sum() if not df_f2.empty else 0
    texto_riesgo = "ESTABLE" if tasa_promedio < 54.5 else "CRÍTICO"
    color_riesgo = "#639922" if texto_riesgo == "ESTABLE" else CNH_ROJO

    kpi1 = crear_kpi("Tasa Incumplimiento (Histórica)", f"{tasa_promedio:.1f}%", "Falla Estructural", CNH_ROJO)
    kpi2 = crear_kpi("Equipos en Ventana Crítica", f"{unidades_criticas:,}", "Próximos 30 días", CNH_OSCURO)
    kpi3 = crear_kpi("Volumen de Servicios Urgentes", f"{len(en_ventana[en_ventana['prioridad'] == 'URGENTE']):,}", "< 7 días restantes", COLORES_PRIORIDAD['URGENTE'])
    kpi4 = crear_kpi("Estatus de Alerta Marca", texto_riesgo, "Vs Umbral 54.5%", color_riesgo)

    # --- GRÁFICA 1: BARRAS POR UMBRAL (Predictiva) ---
    fig1 = go.Figure()
    if not en_ventana.empty:
        conteo = en_ventana.groupby('umbral_proximo')['modelo_calc'].count()
        conteo.index = pd.to_numeric(conteo.index, errors='coerce')
        conteo = conteo.reindex(UMBRALES, fill_value=0)
    else:
        conteo = pd.Series([0]*len(UMBRALES), index=UMBRALES)

    fig1.add_trace(go.Bar(
        x=UMBRAL_LABELS, y=conteo.values, name=titulo_fam,
        marker_color=[COLORES_UMBRAL[u] for u in UMBRALES],
        text=conteo.values, textposition='outside', textfont=dict(size=12),
        hovertemplate='<b>Umbral: %{x}</b><br>Unidades: %{y}<extra></extra>'
    ))
    estilo_base(fig1, f'<b>Equipos Proyectados — {titulo_fam}</b>')
    fig1.update_layout(xaxis_title='Umbral de mantenimiento', yaxis_title='Número de unidades', showlegend=False, height=300, margin=dict(t=40, b=40, l=50, r=20))

    # --- GRÁFICA 2: SERIE TEMPORAL (Histórica) ---
    fig2 = go.Figure()
    y_min, y_max = 50, 60 
    if not df_f2.empty:
        df_res = df_f2.groupby('ciclo')['tasa_incumplimiento'].mean().reset_index()
        ciclos_orden = ["Siembra O-I", "Transicion", "Siembra P-V", "Reposo", "Cosecha P-V"]
        df_res['ciclo'] = pd.Categorical(df_res['ciclo'], categories=ciclos_orden, ordered=True)
        df_res = df_res.sort_values('ciclo')

        min_real = df_res['tasa_incumplimiento'].min()
        max_real = df_res['tasa_incumplimiento'].max()
        y_min = min(min_real - 1.5, 53.0)
        y_max = max(max_real + 1.5, 56.0)

        fig2.add_trace(go.Scatter(
            x=df_res['ciclo'], y=df_res['tasa_incumplimiento'],
            mode='lines+markers', name='Tasa de Incumplimiento',
            line=dict(color='#1f77b4', width=4), marker=dict(size=10, color='#1f77b4', symbol='circle'),
            hovertemplate='<b>Ciclo:</b> %{x}<br><b>Tasa:</b> %{y:.1f}%<extra></extra>'
        ))
    
    fig2.add_hrect(y0=53.5, y1=55.5, fillcolor="red", opacity=0.15, line_width=0, name="Umbral de Referencia")
    fig2.add_hline(y=54.5, line_dash="dash", line_color="red", line_width=2, annotation_text="Línea de Falla Estructural (54.5%)", annotation_position="bottom left", annotation_font=dict(color="red", size=11))
    fig2.update_layout(title=dict(text="<b>Falla Estructural sin Variación Estacional</b>", x=0.02, y=0.93), xaxis=dict(title="Ciclo de Siembra", gridcolor='#f5f5f5', type='category'), yaxis=dict(title="Tasa de Incumplimiento (%)", range=[y_min, y_max], gridcolor='#e9e9e9', ticksuffix="%"), template="plotly_white", margin=dict(t=40, b=40, l=50, r=20), hovermode="x unified", height=300)

    # --- GRÁFICA 3: DISTRIBUIDORES PREDICTIVA (Volumen Proyectado) ---
    fig3 = go.Figure()
    if not en_ventana.empty:
        dist_grp = en_ventana.groupby('distribuidor_calc')['modelo_calc'].count().reset_index(name='unidades')
        # Filtramos "Desconocido" si no aporta valor o lo dejamos, tomamos el Top 10 con más trabajo proyectado
        dist_top = dist_grp.sort_values('unidades', ascending=True).tail(10)
        
        fig3.add_trace(go.Bar(
            y=dist_top['distribuidor_calc'], x=dist_top['unidades'], orientation='h',
            marker_color=CNH_ROJO, text=dist_top['unidades'],
            textposition='outside', hovertemplate='<b>%{y}</b><br>Equipos en ventana (<30 días): %{x}<extra></extra>'
        ))
        
        fig3.update_layout(title=dict(text=f"<b>Los Distribuidores con más flujo proyectado</b>", font=dict(size=13), x=0.02), xaxis_title="Volumen de Equipos (Próximos 30 días)", yaxis_title="", template="plotly_white", margin=dict(t=40, b=40, l=150, r=40), xaxis=dict(gridcolor=CNH_GRIS_CLARO), height=300)
    else:
        fig3 = empty

    # --- GRÁFICA 4: DONA DE PRIORIDAD PREDICTIVA ---
    fig4 = go.Figure()
    if not en_ventana.empty:
        prio_grp = en_ventana.groupby('prioridad')['modelo_calc'].count().reset_index(name='unidades')
        
        # Mapeamos los colores exactos para Urgente, Próximo y Planificar
        colores_dona = [COLORES_PRIORIDAD.get(p, CNH_GRIS) for p in prio_grp['prioridad']]
        
        fig4.add_trace(go.Pie(
            labels=prio_grp['prioridad'], values=prio_grp['unidades'], hole=0.55,
            marker_colors=colores_dona, textinfo='percent+label', textposition='inside',
            hovertemplate='<b>%{label}</b><br>Equipos: %{value}<extra></extra>'
        ))
        fig4.update_layout(margin=dict(t=20, b=20, l=20, r=20), showlegend=False, height=300)
    else:
        fig4 = empty

    return [kpi1, kpi2, kpi3, kpi4, fig1, fig2, fig3, fig4]