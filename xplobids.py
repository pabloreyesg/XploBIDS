import streamlit as st
from bids import BIDSLayout
import pandas as pd
import os
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

BASE_DIR = "/media/hdblue1/data_reyes.p/datalad_redlat/data_bids/"
LOG_PATH = "/media/hdblue1/data_reyes.p/datalad_redlat/streamlit_app/invalid_json_log.txt"

# Configuración de página mejorada
st.set_page_config(
    page_title="Explorador BIDS por Grupo y Tipo", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Título con emojis y estilo
st.markdown("""
<div style="text-align: center; padding: 20px; background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); border-radius: 10px; margin-bottom: 30px;">
    <h1 style="color: white; margin: 0;">🧠 Explorador de Archivos BIDS por Grupo y Tipo</h1>
    <p style="color: white; opacity: 0.9; margin: 10px 0 0 0;">Análisis visual de neuroimágenes BIDS</p>
</div>
""", unsafe_allow_html=True)

# Paleta de colores personalizada
COLORES_TIPOS = {
    "T1w": "#FF6B6B",      # Rojo coral
    "T2w": "#4ECDC4",      # Turquesa
    "FLAIR": "#45B7D1",    # Azul cielo
    "dwi": "#96CEB4",      # Verde menta
    "swi": "#FFEAA7",      # Amarillo suave
    "rest": "#FF9F43",     # Naranja
    "asl": "#DDA0DD",      # Violeta
    "otro": "#95A5A6"      # Gris
}

COLORES_GRUPOS = px.colors.qualitative.Set3

@st.cache_resource
def cargar_layout_robusto(base_dir):
    """Carga el layout BIDS manejando archivos JSON corruptos"""
    corrupted_files = []
    
    with st.spinner("🔍 Escaneando archivos JSON..."):
        for root, _, files in os.walk(base_dir):
            for fname in files:
                if fname.endswith(".json"):
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r") as f:
                            json.load(f)
                    except Exception:
                        corrupted_files.append(fpath)
    
    if corrupted_files:
        st.info(f"📝 Procesando {len(corrupted_files)} archivos JSON corruptos...")
        with open(LOG_PATH, "w") as logf:
            for f in corrupted_files:
                try:
                    os.rename(f, f + ".invalid")
                    logf.write(f + "\n")
                except Exception as e:
                    st.error(f"❌ No se pudo renombrar {f}: {e}")
    
    return BIDSLayout(base_dir, validate=False)

# Cargar layout
layout = cargar_layout_robusto(BASE_DIR)

# Sidebar con información y filtros
with st.sidebar:
    st.markdown("### 📊 Información del Dataset")
    st.markdown(f"**📁 Directorio base:** {BASE_DIR}")
    
    # Mostrar archivos .json.invalid
    st.markdown("### ⚠️ Archivos JSON Inválidos")
    invalid_files = []
    for root, _, files in os.walk(BASE_DIR):
        for fname in files:
            if fname.endswith(".json.invalid"):
                invalid_files.append(os.path.join(root, fname))
    
    if invalid_files:
        st.warning(f"🔍 {len(invalid_files)} archivos inválidos encontrados")
        with st.expander("Ver archivos inválidos"):
            for f in invalid_files:
                st.code(os.path.basename(f), language="text")
    else:
        st.success("✅ No hay archivos JSON inválidos")
    
    st.markdown("---")
    
    # NUEVO: Filtro para archivos "otros"
    st.markdown("### 🔧 Filtros de Calidad de Datos")
    
    # Checkbox para incluir/excluir archivos "otros"
    incluir_otros = st.checkbox(
        "🗂️ Incluir archivos 'otros'", 
        value=True,
        help="Los archivos 'otros' pueden sesgar los resultados. Desactiva para un análisis más preciso."
    )
    
    # Slider para filtrar tipos con pocos archivos
    min_archivos_tipo = st.slider(
        "📊 Mínimo de archivos por tipo",
        min_value=1,
        max_value=20,
        value=1,
        help="Excluye tipos de imagen con menos archivos del análisis"
    )
    
    # Información sobre el filtrado
    if not incluir_otros:
        st.info("🎯 Archivos 'otros' excluidos del análisis")
    
    if min_archivos_tipo > 1:
        st.info(f"🔍 Solo tipos con ≥{min_archivos_tipo} archivos")

# Clasificar archivos
archivo_tipo = []
keywords = ["T1w", "T2w", "FLAIR", "dwi", "swi", "asl"]

if layout:
    try:
        with st.spinner("📂 Clasificando archivos..."):
            files = layout.get(return_type="file", extension=[".nii", ".nii.gz"])
            
            progress_bar = st.progress(0)
            for i, f in enumerate(files):
                tipo = "otro"
                f_lower = os.path.basename(f).lower()
                
                if "/func/" in f and ("rest" in f_lower or "resting" in f_lower):
                    tipo = "rest"
                else:
                    for key in keywords:
                        if key.lower() in f_lower:
                            tipo = key
                            break
                
                grupo = "ND"
                parts = f_lower.split("_")[0]
                if parts.startswith("sub-") and len(parts) >= 6:
                    grupo = parts[4:6].upper()
                
                archivo_tipo.append({"archivo": f, "tipo": tipo, "grupo": grupo})
                progress_bar.progress((i + 1) / len(files))
            
            progress_bar.empty()
            
    except Exception as e:
        st.error(f"❌ Error leyendo archivos: {e}")

df_archivos = pd.DataFrame(archivo_tipo)

# NUEVO: Aplicar filtros de calidad de datos
df_original = df_archivos.copy()

# Filtrar archivos "otros" si está desactivado
if not incluir_otros:
    df_archivos = df_archivos[df_archivos["tipo"] != "otro"]

# Filtrar tipos con pocos archivos
if min_archivos_tipo > 1:
    conteos_tipo = df_archivos["tipo"].value_counts()
    tipos_validos = conteos_tipo[conteos_tipo >= min_archivos_tipo].index
    df_archivos = df_archivos[df_archivos["tipo"].isin(tipos_validos)]

# Mostrar información sobre el filtrado
col1, col2 = st.columns(2)
with col1:
    st.info(f"📊 **Archivos originales:** {len(df_original)}")
with col2:
    st.info(f"📊 **Archivos después de filtros:** {len(df_archivos)}")

# Métricas principales
if not df_archivos.empty:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📁 Total de Archivos", len(df_archivos))
    
    with col2:
        st.metric("👥 Grupos Únicos", df_archivos["grupo"].nunique())
    
    with col3:
        st.metric("🔬 Tipos de Imagen", df_archivos["tipo"].nunique())
    
    with col4:
        st.metric("📊 Sujetos Únicos", 
                 len([f for f in df_archivos["archivo"] if "sub-" in f]))

# Gráfico principal: Total por grupo
st.markdown("### 📊 Distribución de Archivos por Grupo")

conteo_grupos = df_archivos["grupo"].value_counts().sort_index()

fig_grupos = go.Figure(data=[
    go.Bar(
        x=conteo_grupos.index,
        y=conteo_grupos.values,
        text=conteo_grupos.values,
        textposition='auto',
        marker_color=COLORES_GRUPOS[:len(conteo_grupos)],
        hovertemplate='<b>Grupo %{x}</b><br>Archivos: %{y}<extra></extra>',
        marker_line_color='white',
        marker_line_width=2
    )
])

fig_grupos.update_layout(
    title="Distribución de Archivos por Grupo",
    xaxis_title="Grupo",
    yaxis_title="Número de Archivos",
    showlegend=False,
    height=400,
    template="plotly_white",
    plot_bgcolor='rgba(248,249,250,1)'
)

st.plotly_chart(fig_grupos, use_container_width=True)

# Gráfico detallado por tipo
st.markdown("### 🔬 Análisis Detallado por Tipo de Imagen")

grupo_opciones = sorted(df_archivos["grupo"].dropna().unique())
grupo_seleccionado = st.selectbox("🎯 Seleccionar grupo para análisis detallado", grupo_opciones)

df_grupo = df_archivos[df_archivos["grupo"] == grupo_seleccionado]
orden = ["T1w", "T2w", "FLAIR", "dwi", "swi", "rest", "asl", "otro"]
conteo_tipo = df_grupo["tipo"].value_counts().reindex(orden, fill_value=0)

# Crear gráfico horizontal con colores
fig_tipos = go.Figure(data=[
    go.Bar(
        x=conteo_tipo.values,
        y=conteo_tipo.index,
        text=conteo_tipo.values,
        textposition='auto',
        marker_color=[COLORES_TIPOS.get(tipo, "#95A5A6") for tipo in conteo_tipo.index],
        hovertemplate='<b>%{y}</b><br>Archivos: %{x}<extra></extra>',
        orientation='h',
        marker_line_color='white',
        marker_line_width=2
    )
])

fig_tipos.update_layout(
    title=f"Distribución de Tipos de Imagen - Grupo {grupo_seleccionado}",
    xaxis_title="Número de Archivos",
    yaxis_title="Tipo de Imagen",
    showlegend=False,
    height=500,
    template="plotly_white",
    plot_bgcolor='rgba(248,249,250,1)'
)

st.plotly_chart(fig_tipos, use_container_width=True)

# Gráficos complementarios
col1, col2 = st.columns([1, 2])  # Hacer la columna del heatmap más grande

with col1:
    # Gráfico de dona para el grupo seleccionado
    if conteo_tipo.sum() > 0:
        conteo_positivo = conteo_tipo[conteo_tipo > 0]
        colores_positivos = [COLORES_TIPOS.get(tipo, "#95A5A6") for tipo in conteo_positivo.index]
        
        fig_dona = go.Figure(data=[
            go.Pie(
                labels=conteo_positivo.index,
                values=conteo_positivo.values,
                hole=0.4,
                marker_colors=colores_positivos,
                hovertemplate='<b>%{label}</b><br>Archivos: %{value}<br>Porcentaje: %{percent}<extra></extra>',
                textinfo='label+percent',
                textposition='auto'
            )
        ])
        
        fig_dona.update_layout(
            title=f"Composición de Tipos - Grupo {grupo_seleccionado}",
            height=500,
            template="plotly_white",
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            )
        )
        
        st.plotly_chart(fig_dona, use_container_width=True)

with col2:
    # MEJORADO: Heatmap más grande con mejor paleta de colores
    st.markdown("#### 🌡️ Mapa de Calor - Grupos vs Tipos")
    
    pivot_table = df_archivos.pivot_table(
        values="archivo", 
        index="grupo", 
        columns="tipo", 
        aggfunc="count", 
        fill_value=0
    )
    
    # Nueva paleta de colores: de azul claro a azul oscuro (mejor legibilidad)
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=pivot_table.columns,
        y=pivot_table.index,
        colorscale=[
            [0, '#f0f9ff'],      # Azul muy claro
            [0.2, '#bae6fd'],    # Azul claro
            [0.4, '#7dd3fc'],    # Azul medio-claro
            [0.6, '#38bdf8'],    # Azul medio
            [0.8, '#0284c7'],    # Azul oscuro
            [1, '#0c4a6e']       # Azul muy oscuro
        ],
        hovertemplate='<b>Grupo: %{y}</b><br>Tipo: %{x}<br>Archivos: %{z}<extra></extra>',
        colorbar=dict(
            title="Número de Archivos",
            titleside="right",
            tickmode="linear",
            thickness=20
        ),
        text=pivot_table.values,
        texttemplate="%{text}",
        textfont={"size": 14, "color": "white", "family": "Arial Black"},
        showscale=True
    ))
    
    fig_heatmap.update_layout(
        title="Matriz de Distribución: Grupos vs Tipos de Imagen",
        xaxis_title="Tipo de Imagen",
        yaxis_title="Grupo",
        height=500,  # Aumentado de 400 a 500
        template="plotly_white",
        font=dict(size=12),
        xaxis=dict(
            tickangle=45,
            tickfont=dict(size=11)
        ),
        yaxis=dict(
            tickfont=dict(size=11)
        )
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True)

# Filtros interactivos
st.markdown("### 🔍 Filtros Interactivos")

col1, col2 = st.columns(2)

with col1:
    grupos_sel = st.multiselect(
        "👥 Filtrar por grupo", 
        grupo_opciones, 
        default=grupo_opciones,
        help="Selecciona uno o más grupos para filtrar"
    )

with col2:
    tipos_opciones = sorted(df_archivos["tipo"].dropna().unique())
    tipos_sel = st.multiselect(
        "🔬 Filtrar por tipo", 
        tipos_opciones, 
        default=tipos_opciones,
        help="Selecciona uno o más tipos de imagen para filtrar"
    )

# Aplicar filtros
df_filtrado = df_archivos[
    (df_archivos["grupo"].isin(grupos_sel)) & 
    (df_archivos["tipo"].isin(tipos_sel))
]

# Mostrar resultados filtrados
st.markdown("### 📋 Resultados Filtrados")
st.info(f"📊 Mostrando {len(df_filtrado)} archivos de {len(df_archivos)} totales")

# Tabla con estilo
df_display = df_filtrado[["archivo", "tipo", "grupo"]].rename(columns={
    "archivo": "🗂️ Archivo", 
    "tipo": "🔬 Tipo", 
    "grupo": "👥 Grupo"
})

st.dataframe(
    df_display, 
    use_container_width=True,
    hide_index=True
)

# Gráficos de resumen de filtros
if not df_filtrado.empty:
    st.markdown("### 📈 Resumen de Datos Filtrados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de barras para tipos filtrados
        tipo_counts = df_filtrado["tipo"].value_counts()
        colores_filtrados = [COLORES_TIPOS.get(tipo, "#95A5A6") for tipo in tipo_counts.index]
        
        fig_tipos_filt = go.Figure(data=[
            go.Bar(
                x=tipo_counts.index,
                y=tipo_counts.values,
                text=tipo_counts.values,
                textposition='auto',
                marker_color=colores_filtrados,
                hovertemplate='<b>%{x}</b><br>Archivos: %{y}<extra></extra>',
                marker_line_color='white',
                marker_line_width=2
            )
        ])
        
        fig_tipos_filt.update_layout(
            title="Tipos de Imagen (Filtrados)",
            xaxis_title="Tipo",
            yaxis_title="Cantidad",
            showlegend=False,
            height=400,
            template="plotly_white",
            plot_bgcolor='rgba(248,249,250,1)'
        )
        
        st.plotly_chart(fig_tipos_filt, use_container_width=True)
    
    with col2:
        # Gráfico de barras para grupos filtrados
        grupo_counts = df_filtrado["grupo"].value_counts()
        
        fig_grupos_filt = go.Figure(data=[
            go.Bar(
                x=grupo_counts.index,
                y=grupo_counts.values,
                text=grupo_counts.values,
                textposition='auto',
                marker_color=COLORES_GRUPOS[:len(grupo_counts)],
                hovertemplate='<b>Grupo %{x}</b><br>Archivos: %{y}<extra></extra>',
                marker_line_color='white',
                marker_line_width=2
            )
        ])
        
        fig_grupos_filt.update_layout(
            title="Grupos (Filtrados)",
            xaxis_title="Grupo",
            yaxis_title="Cantidad",
            showlegend=False,
            height=400,
            template="plotly_white",
            plot_bgcolor='rgba(248,249,250,1)'
        )
        
        st.plotly_chart(fig_grupos_filt, use_container_width=True)

# NUEVO: Sección de estadísticas de filtrado
if not incluir_otros or min_archivos_tipo > 1:
    st.markdown("### 📊 Estadísticas de Filtrado")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        archivos_excluidos = len(df_original) - len(df_archivos)
        st.metric(
            "📉 Archivos Excluidos", 
            archivos_excluidos,
            delta=f"{archivos_excluidos/len(df_original)*100:.1f}% del total"
        )
    
    with col2:
        if not incluir_otros:
            otros_excluidos = len(df_original[df_original["tipo"] == "otro"])
            st.metric(
                "🗂️ Archivos 'Otros' Excluidos", 
                otros_excluidos
            )
    
    with col3:
        if min_archivos_tipo > 1:
            tipos_excluidos = len(df_original["tipo"].unique()) - len(df_archivos["tipo"].unique())
            st.metric(
                "🔬 Tipos Excluidos", 
                tipos_excluidos
            )

# Opción para ver archivos listados
if st.checkbox("📄 Ver lista detallada de archivos"):
    st.markdown("### 📂 Lista de Archivos")
    for i, f in enumerate(df_filtrado["archivo"], 1):
        st.code(f"{i:03d}: {f}", language="text")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>🧠 Explorador BIDS | Desarrollado por Pablo Reyes | Versión Mejorada</p>
</div>
""", unsafe_allow_html=True)