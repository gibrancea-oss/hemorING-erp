import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import qrcode
import io
import base64
import time
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Hemore - ERP", layout="wide", page_icon="🛠️")

# --- CONEXIÓN A GOOGLE SHEETS ---
# Esta función conecta con tu "Almacén" en la nube
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

# --- ESTILOS CSS (Igual que antes) ---
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    div[data-testid="stSidebarUserContent"] { padding-top: 2rem; }
    .hoja-carta {
        width: 21.59cm; min-height: 27.94cm; background-color: white;
        padding: 0.5cm; margin: 0 auto; border: 1px solid #ddd;
        display: flex; flex-wrap: wrap; align-content: flex-start; gap: 0.2cm;
    }
    .etiqueta-print {
        width: 5cm; height: 2.5cm; border: 1px dotted #ccc;
        display: flex; flex-direction: row; align-items: center;
        justify-content: flex-start; background: white;
        box-sizing: border-box; overflow: hidden; padding: 2px;
        page-break-inside: avoid; color: black;
    }
    .etiqueta-print img { width: 1.8cm !important; height: 1.8cm !important; display: block; margin-right: 4px; }
    .etiqueta-text { font-size: 7pt; font-family: Arial, sans-serif; line-height: 1.1; width: 100%; word-wrap: break-word; max-height: 2.3cm; overflow: hidden; text-align: left; }
    @media print {
        @page { size: letter; margin: 0.5cm; }
        [data-testid="stSidebar"], header, footer, .stTextInput, .stRadio, .stToggle, button, .stApp > header { display: none !important; }
        .block-container { padding: 0 !important; margin: 0 !important; }
        .hoja-carta { border: none; width: 100%; padding: 0; gap: 1mm; }
        .etiqueta-print { border: 1px solid #000; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN DE LOGIN ---
def verificar_password():
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
    
    if st.session_state.autenticado:
        return True

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.info("👋 Bienvenido al Sistema de Gestión (Nube)")
        st.title("🔐 Acceso Restringido")
        
        password = st.text_input("Ingrese la contraseña", type="password")
        if st.button("Entrar", type="primary"):
            # Aquí podrías cambiar la contraseña si quieres
            if password == "HEMORE2026":
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta")
    return False

# --- FUNCIONES DE BASE DE DATOS (NUBE) ---
def cargar_datos():
    conn = get_connection()
    # ttl=0 obliga a leer los datos frescos de la nube, no de la memoria caché
    try:
        df_ops = conn.read(worksheet="Operadores", ttl=0)
        df_ins = conn.read(worksheet="Insumos", ttl=0)
        df_hi_ins = conn.read(worksheet="Historial_Insumos", ttl=0)
        df_her = conn.read(worksheet="Herramientas", ttl=0)
        df_hi_her = conn.read(worksheet="Historial_Herramientas", ttl=0)
        
        # Limpieza básica para evitar errores si vienen vacíos
        df_ops = df_ops if not df_ops.empty else pd.DataFrame(columns=['Nombre_Operador', 'Tipo'])
        df_ins = df_ins if not df_ins.empty else pd.DataFrame(columns=['ID', 'Insumo', 'Descripcion', 'Cantidad', 'Unidad', 'Stock_Minimo'])
        df_hi_ins = df_hi_ins if not df_hi_ins.empty else pd.DataFrame(columns=['Fecha_Hora', 'Insumo', 'Descripcion', 'Cantidad', 'Unidad', 'Entregado_A'])
        df_her = df_her if not df_her.empty else pd.DataFrame(columns=['ID', 'ID_Herramienta', 'Herramienta', 'Descripcion', 'Marca', 'Estado', 'Responsable'])
        df_hi_her = df_hi_her if not df_hi_her.empty else pd.DataFrame(columns=['Fecha_Hora', 'Herramienta', 'Movimiento', 'Responsable', 'Detalle'])
        
        # Convertir tipos numéricos
        if not df_ins.empty:
            df_ins['Cantidad'] = pd.to_numeric(df_ins['Cantidad'], errors='coerce').fillna(0)
            df_ins['ID'] = pd.to_numeric(df_ins['ID'], errors='coerce').fillna(0).astype(int)

        if not df_her.empty:
             df_her['ID'] = pd.to_numeric(df_her['ID'], errors='coerce').fillna(0).astype(int)
             df_her['Responsable'] = df_her['Responsable'].fillna("Bodega").astype(str)

        return df_ops, df_ins, df_hi_ins, df_her, df_hi_her

    except Exception as e:
        st.error(f"Error conectando con Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def guardar_datos(df_o, df_i, df_hi_ins, df_h, df_hi_her):
    conn = get_connection()
    try:
        # Escribimos en cada pestaña correspondiente
        conn.update(worksheet="Operadores", data=df_o)
        conn.update(worksheet="Insumos", data=df_i)
        conn.update(worksheet="Historial_Insumos", data=df_hi_ins)
        conn.update(worksheet="Herramientas", data=df_h)
        conn.update(worksheet="Historial_Herramientas", data=df_hi_her)
        return True
    except Exception as e:
        st.error(f"Error al guardar en la nube: {e}")
        return False

def filtrar_dataframe(df, texto):
    if not texto or df.empty: return df
    palabras = texto.lower().split()
    def match_row(row):
        return all(p in " ".join(row.astype(str)).lower() for p in palabras)
    return df[df.apply(match_row, axis=1)]

def generar_qr_b64(texto):
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=0)
        qr.add_data(str(texto))
        qr.make(fit=True)
        buffer = io.BytesIO()
        qr.make_image(fill='black', back_color='white').save(buffer, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
    except: return None

# --- APP PRINCIPAL ---
if verificar_password():
    # Cargar datos al inicio
    if 'db_insumos' not in st.session_state:
        with st.spinner('Conectando con la base de datos...'):
            (st.session_state.db_operadores, st.session_state.db_insumos, 
             st.session_state.db_hist_insumos, st.session_state.db_herramientas, 
             st.session_state.db_hist_herramientas) = cargar_datos()

    with st.sidebar:
        st.title("📦 HEMORE ERP")
        st.caption("Versión Cloud ☁️")
        st.divider()
        menu = st.radio("NAVEGACIÓN", ["📈 Dashboard", "📦 Gestión de Insumos", "🔧 Gestión de Herramientas", "🆔 Catálogo de IDs", "⚙️ Configuración & Datos"])
        st.divider()
        if st.button("Cerrar Sesión"):
            st.session_state.autenticado = False
            st.rerun()
        if st.button("🔄 Recargar Datos"):
            st.cache_data.clear()
            del st.session_state.db_insumos
            st.rerun()

    # --- DASHBOARD ---
    if menu == "📈 Dashboard":
        st.header("📈 Dashboard General")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📦 Insumos")
            if not st.session_state.db_insumos.empty:
                df_i = st.session_state.db_insumos
                st.plotly_chart(px.bar(df_i, x='Insumo', y='Cantidad', title="Stock Insumos"), use_container_width=True)
        with col2:
            st.subheader("🔧 Herramientas")
            if not st.session_state.db_herramientas.empty:
                df_h = st.session_state.db_herramientas.copy()
                df_h['Situación'] = df_h['Responsable'].apply(lambda x: 'Disponible (Bodega)' if x == 'Bodega' else 'Prestado')
                st.metric("Total Activos Fijos", len(df_h))
                st.plotly_chart(px.pie(df_h, names='Situación', title="Disponibilidad Actual"), use_container_width=True)

    # --- INSUMOS ---
    elif menu == "📦 Gestión de Insumos":
        st.header("📦 Insumos")
        tab1, tab2, tab3 = st.tabs(["Inventario", "Movimientos", "Historial"])
        
        with tab1:
            search = st.text_input("Buscar Insumo", key="s_ins")
            df = filtrar_dataframe(st.session_state.db_insumos, search)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        with tab2:
            l_ins = [f"{r['ID']} - {r['Insumo']} | Desc: {r['Descripcion']}" for i, r in st.session_state.db_insumos.iterrows()]
            c1, c2 = st.columns(2)
            if l_ins:
                with c1.form("salida"):
                    st.subheader("Salida")
                    s_item = st.selectbox("Seleccionar", l_ins, key="sal_ins")
                    cant = st.number_input("Cantidad", 0.01, key="sal_cant")
                    quien = st.selectbox("Solicitante", st.session_state.db_operadores['Nombre_Operador'].astype(str).unique())
                    if st.form_submit_button("Registrar Salida"):
                        idx = st.session_state.db_insumos[st.session_state.db_insumos['ID'].astype(str) == s_item.split(' - ')[0]].index[0]
                        if st.session_state.db_insumos.at[idx, 'Cantidad'] >= cant:
                            st.session_state.db_insumos.at[idx, 'Cantidad'] -= cant
                            nombre = s_item.split(' - ')[1].split(' |')[0]
                            reg = pd.DataFrame([[datetime.now().strftime('%d/%m/%Y %H:%M'), nombre, "Salida", cant, "Unidad", quien]], columns=st.session_state.db_hist_insumos.columns)
                            st.session_state.db_hist_insumos = pd.concat([st.session_state.db_hist_insumos, reg], ignore_index=True)
                            
                            if guardar_datos(st.session_state.db_operadores, st.session_state.db_insumos, st.session_state.db_hist_insumos, st.session_state.db_herramientas, st.session_state.db_hist_herramientas):
                                st.success("✅ Salida Guardada en Nube")
                                time.sleep(1)
                                st.rerun()
                        else: st.error("❌ Stock insuficiente")
                with c2.form("entrada"):
                    st.subheader("Entrada")
                    e_item = st.selectbox("Seleccionar", l_ins, key="ent_ins")
                    e_cant = st.number_input("Cantidad", 0.01, key="ent_cant")
                    if st.form_submit_button("Registrar Entrada"):
                        idx = st.session_state.db_insumos[st.session_state.db_insumos['ID'].astype(str) == e_item.split(' - ')[0]].index[0]
                        st.session_state.db_insumos.at[idx, 'Cantidad'] += e_cant
                        nombre = e_item.split(' - ')[1].split(' |')[0]
                        reg = pd.DataFrame([[datetime.now().strftime('%d/%m/%Y %H:%M'), nombre, "Entrada", e_cant, "Unidad", "Almacén"]], columns=st.session_state.db_hist_insumos.columns)
                        st.session_state.db_hist_insumos = pd.concat([st.session_state.db_hist_insumos, reg], ignore_index=True)
                        
                        if guardar_datos(st.session_state.db_operadores, st.session_state.db_insumos, st.session_state.db_hist_insumos, st.session_state.db_herramientas, st.session_state.db_hist_herramientas):
                            st.success("✅ Entrada Guardada en Nube")
                            time.sleep(1)
                            st.rerun()

        with tab3:
            st.dataframe(st.session_state.db_hist_insumos.iloc[::-1], use_container_width=True)

    # --- HERRAMIENTAS ---
    elif menu == "🔧 Gestión de Herramientas":
        st.header("🔧 Herramientas")
        tab1, tab2, tab3 = st.tabs(["Inventario", "Préstamos/Devoluciones", "Historial"])
        
        with tab1:
            search = st.text_input("Buscar Herramienta", key="s_her")
            df = filtrar_dataframe(st.session_state.db_herramientas, search)
            df['Ubicación'] = df['Responsable'].apply(lambda x: "🟢 BODEGA" if x == 'Bodega' else f"🔴 PRESTADO A: {x}")
            st.dataframe(df[['ID', 'ID_Herramienta', 'Herramienta', 'Marca', 'Estado', 'Ubicación']], use_container_width=True, hide_index=True)

        with tab2:
            df_h = st.session_state.db_herramientas
            l_disp = [f"{r['ID']} - [{r['ID_Herramienta']}] {r['Herramienta']} | {r['Marca']}" for i, r in df_h[df_h['Responsable']=='Bodega'].iterrows()]
            l_pres = [f"{r['ID']} - [{r['ID_Herramienta']}] {r['Herramienta']} | Tiene: {r['Responsable']}" for i, r in df_h[df_h['Responsable']!='Bodega'].iterrows()]
            
            c1, c2 = st.columns(2)
            if l_disp:
                with c1.form("prestamo"):
                    st.subheader("Prestar (Salida)")
                    p_item = st.selectbox("Seleccionar Herramienta", l_disp)
                    p_op = st.selectbox("Operador", st.session_state.db_operadores['Nombre_Operador'].astype(str).unique())
                    if st.form_submit_button("Prestar"):
                        idx = df_h[df_h['ID'].astype(str) == p_item.split(' - ')[0]].index[0]
                        st.session_state.db_herramientas.at[idx, 'Responsable'] = p_op
                        nom = p_item.split('] ')[1].split(' |')[0]
                        reg = pd.DataFrame([[datetime.now().strftime('%d/%m/%Y %H:%M'), nom, "Préstamo", p_op, ""]], columns=st.session_state.db_hist_herramientas.columns)
                        st.session_state.db_hist_herramientas = pd.concat([st.session_state.db_hist_herramientas, reg], ignore_index=True)
                        
                        if guardar_datos(st.session_state.db_operadores, st.session_state.db_insumos, st.session_state.db_hist_insumos, st.session_state.db_herramientas, st.session_state.db_hist_herramientas):
                            st.success("✅ Préstamo Guardado")
                            time.sleep(1)
                            st.rerun()

            if l_pres:
                with c2.form("devolucion"):
                    st.subheader("Devolver (Entrada)")
                    d_item = st.selectbox("Seleccionar Herramienta", l_pres)
                    d_est = st.selectbox("Estado", ["BUENO", "MALO"])
                    if st.form_submit_button("Devolver"):
                        idx = df_h[df_h['ID'].astype(str) == d_item.split(' - ')[0]].index[0]
                        st.session_state.db_herramientas.at[idx, 'Responsable'] = "Bodega"
                        st.session_state.db_herramientas.at[idx, 'Estado'] = d_est
                        nom = d_item.split('] ')[1].split(' |')[0]
                        reg = pd.DataFrame([[datetime.now().strftime('%d/%m/%Y %H:%M'), nom, "Devolución", "Bodega", d_est]], columns=st.session_state.db_hist_herramientas.columns)
                        st.session_state.db_hist_herramientas = pd.concat([st.session_state.db_hist_herramientas, reg], ignore_index=True)
                        
                        if guardar_datos(st.session_state.db_operadores, st.session_state.db_insumos, st.session_state.db_hist_insumos, st.session_state.db_herramientas, st.session_state.db_hist_herramientas):
                            st.success("✅ Devolución Guardada")
                            time.sleep(1)
                            st.rerun()

        with tab3:
            st.dataframe(st.session_state.db_hist_herramientas.iloc[::-1], use_container_width=True)

    # --- CATÁLOGO IDs ---
    elif menu == "🆔 Catálogo de IDs":
        st.header("🆔 Etiquetas QR")
        busqueda = st.text_input("Buscar", placeholder="Taladro")
        vista = st.radio("Ver:", ["Insumos", "Herramientas"], horizontal=True)
        imprimir = st.toggle("🖨️ Modo Impresión (5x2.5 cm)")
        
        if vista == "Insumos" and not st.session_state.db_insumos.empty:
            df = filtrar_dataframe(st.session_state.db_insumos[['Insumo', 'Descripcion']], busqueda)
            if imprimir:
                html = "<div class='hoja-carta'>"
                for _, row in df.iterrows():
                    qr = generar_qr_b64(row['Insumo'])
                    html += f"<div class='etiqueta-print'><img src='{qr}'><div class='etiqueta-text'><strong>{row['Insumo']}</strong><br>{row['Descripcion']}</div></div>"
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)
            else: st.dataframe(df, use_container_width=True)
            
        elif vista == "Herramientas" and not st.session_state.db_herramientas.empty:
            df = filtrar_dataframe(st.session_state.db_herramientas[['ID_Herramienta', 'Herramienta', 'Descripcion']], busqueda)
            if imprimir:
                html = "<div class='hoja-carta'>"
                for _, row in df.iterrows():
                    qr = generar_qr_b64(row['ID_Herramienta'])
                    html += f"<div class='etiqueta-print'><img src='{qr}'><div class='etiqueta-text'><strong>{row['Herramienta']}</strong><br>{row['Descripcion']}<br>{row['ID_Herramienta']}</div></div>"
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)
            else: st.dataframe(df, use_container_width=True)

    # --- CONFIGURACIÓN ---
    elif menu == "⚙️ Configuración & Datos":
        st.header("⚙️ Datos Maestros")
        t1, t2, t3 = st.tabs(["Personal", "Insumos", "Herramientas"])
        
        with t1:
            st.subheader("Personal")
            edited_op = st.data_editor(st.session_state.db_operadores, num_rows="dynamic", key="ed_op", use_container_width=True)
            if st.button("Guardar Personal"):
                st.session_state.db_operadores = edited_op
                guardar_datos(st.session_state.db_operadores, st.session_state.db_insumos, st.session_state.db_hist_insumos, st.session_state.db_herramientas, st.session_state.db_hist_herramientas)
                st.success("Guardado"); time.sleep(1); st.rerun()

        with t2:
            st.subheader("Insumos")
            edited_ins = st.data_editor(st.session_state.db_insumos, num_rows="dynamic", key="ed_ins", use_container_width=True)
            if st.button("Guardar Insumos"):
                edited_ins['ID'] = range(1, len(edited_ins) + 1) # Auto ID
                st.session_state.db_insumos = edited_ins
                guardar_datos(st.session_state.db_operadores, st.session_state.db_insumos, st.session_state.db_hist_insumos, st.session_state.db_herramientas, st.session_state.db_hist_herramientas)
                st.success("Guardado"); time.sleep(1); st.rerun()

        with t3:
            st.subheader("Herramientas")
            edited_her = st.data_editor(st.session_state.db_herramientas, num_rows="dynamic", key="ed_her", use_container_width=True)
            if st.button("Guardar Herramientas"):
                edited_her['ID'] = range(1, len(edited_her) + 1)
                st.session_state.db_herramientas = edited_her
                guardar_datos(st.session_state.db_operadores, st.session_state.db_insumos, st.session_state.db_hist_insumos, st.session_state.db_herramientas, st.session_state.db_hist_herramientas)
                st.success("Guardado"); time.sleep(1); st.rerun()