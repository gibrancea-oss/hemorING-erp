import streamlit as st
import pandas as pd
import gspread
import plotly.express as px

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="HEMORE ERP", layout="wide")

# --- CONEXIÓN BLINDADA (Usando archivo credentials.json) ---
@st.cache_data(ttl=60)
def cargar_datos():
    try:
        # 1. Busca la llave en la carpeta del proyecto
        gc = gspread.service_account(filename='credentials.json')

        # 2. Abre el Excel por su LINK (Asegúrate de que este sea tu link)
        sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1Vc6hds7rsJMg7TYCdSnr5mTSi-1q13XXMdWI0yXJmlU/edit")

        # 3. Lee las pestañas (Deben llamarse IGUAL en Excel)
        ws_insumos = sh.worksheet("Insumos")
        ws_herramientas = sh.worksheet("Herramientas")

        # 4. Convierte a tablas
        df_ins = pd.DataFrame(ws_insumos.get_all_records())
        df_her = pd.DataFrame(ws_herramientas.get_all_records())

        return df_ins, df_her

    except Exception as e:
        st.error(f"❌ Error de Conexión: {e}")
        return None, None

# --- CARGA DE DATOS ---
df_insumos, df_herramientas = cargar_datos()

if df_insumos is not None:
    # --- MENÚ LATERAL ---
    st.sidebar.title("Navegación")
    menu = st.sidebar.radio("Ir a:", ["Dashboard", "Insumos", "Herramientas"])

    # --- PÁGINA: DASHBOARD ---
    if menu == "Dashboard":
        st.title("📊 Resumen General")
        col1, col2 = st.columns(2)
        col1.metric("📦 Total Insumos", len(df_insumos))
        col2.metric("🛠️ Total Herramientas", len(df_herramientas))

    # --- PÁGINA: INSUMOS ---
    elif menu == "Insumos":
        st.title("📦 Inventario de Insumos")
        st.dataframe(df_insumos, use_container_width=True)

    # --- PÁGINA: HERRAMIENTAS ---
    elif menu == "Herramientas":
        st.title("🛠️ Control de Herramientas")
        busqueda = st.text_input("🔍 Buscar herramienta o responsable:")
        
        if busqueda:
            # Filtro inteligente (busca en todo el texto)
            df_filtrado = df_herramientas[
                df_herramientas.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
            ]
            st.dataframe(df_filtrado, use_container_width=True)
        else:
            st.dataframe(df_herramientas, use_container_width=True)

else:
    st.warning("⚠️ Esperando conexión... Revisa que 'credentials.json' esté en GitHub.")
