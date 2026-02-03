import streamlit as st
import pandas as pd
import gspread
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE LA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="HEMORE ERP",
    page_icon="📦",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. CONEXIÓN ROBUSTA (MÉTODO DEL ARCHIVO)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60) # Se actualiza cada 60 segundos
def cargar_datos():
    try:
        # A) Buscamos la llave en la carpeta
        # Asegúrate de haber subido 'credentials.json' a GitHub
        gc = gspread.service_account(filename='credentials.json')

        # B) Abrimos el Excel por el Link
        url_excel = "https://docs.google.com/spreadsheets/d/1Vc6hds7rsJMg7TYCdSnr5mTSi-1q13XXMdWI0yXJmlU/edit"
        sh = gc.open_by_url(url_excel)

        # C) Leemos las pestañas (Deben llamarse EXACTAMENTE así en Excel)
        ws_insumos = sh.worksheet("Insumos")
        ws_herramientas = sh.worksheet("Herramientas")

        # D) Convertimos a Tablas de Pandas
        df_ins = pd.DataFrame(ws_insumos.get_all_records())
        df_her = pd.DataFrame(ws_herramientas.get_all_records())

        # E) Limpieza de nombres de columnas (para evitar errores de espacios extra)
        # Esto convierte "ID " en "ID" automáticamente
        df_ins.columns = df_ins.columns.str.strip()
        df_her.columns = df_her.columns.str.strip()

        return df_ins, df_her

    except FileNotFoundError:
        st.error("🚨 ERROR: No encuentro el archivo 'credentials.json'. Asegúrate de subirlo a GitHub.")
        st.stop()
    except Exception as e:
        st.error(f"🚨 ERROR DE CONEXIÓN: {e}")
        st.stop()

# --- CARGAMOS LOS DATOS ---
df_insumos, df_herramientas = cargar_datos()

# -----------------------------------------------------------------------------
# 3. BARRA LATERAL (SIDEBAR)
# -----------------------------------------------------------------------------
st.sidebar.title("📦 HEMORE ERP")
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navegación",
    ["📊 Dashboard General", "📦 Insumos", "🛠️ Herramientas"]
)
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Recargar Datos"):
    st.cache_data.clear()
    st.rerun()

# -----------------------------------------------------------------------------
# 4. PÁGINA: DASHBOARD GENERAL
# -----------------------------------------------------------------------------
if menu == "📊 Dashboard General":
    st.title("📊 Dashboard General")
    
    # Métricas principales
    col1, col2, col3 = st.columns(3)
    
    # Calcular totales
    total_insumos = len(df_insumos)
    total_herramientas = len(df_herramientas)
    
    # Intentar calcular herramientas prestadas (si existe la columna Estado)
    prestadas = 0
    if 'Estado' in df_herramientas.columns:
        prestadas = df_herramientas[df_herramientas['Estado'].str.contains('Prestado', case=False, na=False)].shape[0]

    col1.metric("📦 Total Tipos de Insumos", total_insumos)
    col2.metric("🛠️ Total Herramientas", total_herramientas)
    col3.metric("🔴 Herramientas Prestadas", prestadas)

    st.markdown("---")
    
    # Gráfica rápida de Insumos (Si existe columna Cantidad)
    if 'Cantidad' in df_insumos.columns and 'Insumo' in df_insumos.columns:
        st.subheader("📦 Stock de Insumos")
        fig_ins = px.bar(df_insumos, x='Insumo', y='Cantidad', color='Cantidad', title="Niveles de Inventario")
        st.plotly_chart(fig_ins, use_container_width=True)

# -----------------------------------------------------------------------------
# 5. PÁGINA: INSUMOS
# -----------------------------------------------------------------------------
elif menu == "📦 Insumos":
    st.title("📦 Gestión de Insumos")
    
    # Buscador
    busqueda = st.text_input("🔍 Buscar Insumo", "")
    
    # Filtro
    df_filtrado = df_insumos
    if busqueda:
        df_filtrado = df_insumos[
            df_insumos.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
        ]
    
    st.dataframe(df_filtrado, use_container_width=True)
    
    # Alerta de Stock Bajo (Si existen las columnas necesarias)
    if 'Cantidad' in df_insumos.columns and 'Minimo' in df_insumos.columns:
        st.subheader("⚠️ Alerta de Stock Bajo")
        # Convertir a numérico por si acaso
        df_insumos['Cantidad'] = pd.to_numeric(df_insumos['Cantidad'], errors='coerce').fillna(0)
        df_insumos['Minimo'] = pd.to_numeric(df_insumos['Minimo'], errors='coerce').fillna(0)
        
        stock_bajo = df_insumos[df_insumos['Cantidad'] <= df_insumos['Minimo']]
        
        if not stock_bajo.empty:
            st.warning(f"Hay {len(stock_bajo)} insumos por debajo del mínimo.")
            st.dataframe(stock_bajo, use_container_width=True)
        else:
            st.success("✅ Todo el stock está saludable.")

# -----------------------------------------------------------------------------
# 6. PÁGINA: HERRAMIENTAS
# -----------------------------------------------------------------------------
elif menu == "🛠️ Herramientas":
    st.title("🛠️ Gestión de Herramientas")
    
    # Tabs para organizar
    tab1, tab2 = st.tabs(["📋 Inventario Completo", "🔍 Buscador"])
    
    with tab1:
        st.subheader("Listado de Herramientas")
        # Colorear según estado si existe la columna
        if 'Estado' in df_herramientas.columns:
            st.dataframe(
                df_herramientas.style.applymap(
                    lambda x: 'background-color: #ffcdd2' if 'Prestado' in str(x) else '', subset=['Estado']
                ),
                use_container_width=True
            )
        else:
            st.dataframe(df_herramientas, use_container_width=True)

    with tab2:
        st.subheader("Buscador de Herramientas")
        texto_busqueda = st.text_input("Escribe ID, Nombre o Responsable:")
        
        if texto_busqueda:
            resultados = df_herramientas[
                df_herramientas.astype(str).apply(lambda x: x.str.contains(texto_busqueda, case=False, na=False)).any(axis=1)
            ]
            st.write(f"Resultados encontrados: {len(resultados)}")
            st.dataframe(resultados, use_container_width=True)

# -----------------------------------------------------------------------------
# FIN DEL CÓDIGO
# -----------------------------------------------------------------------------
