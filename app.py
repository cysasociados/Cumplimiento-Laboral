import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}</style>", unsafe_allow_html=True)

# URL DEL APPS SCRIPT (Puente a Drive)
URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs DE GOOGLE SHEETS (Los dos archivos con los que trabajamos)
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y" # Estado de Avance
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" # ID_Empresas

# IDs Adicionales
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

# --- FUNCIONES DE LIMPIEZA ---
def limpiar_val(v):
    if pd.isna(v): return ""
    return re.sub(r'[^A-Z0-9]', '', str(v).upper().strip())

def encontrar_columna(df, palabra):
    for col in df.columns:
        if palabra.upper() in col.upper(): return col
    return None

@st.cache_data(ttl=30)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# Inicializar LOG
if "log_accesos" not in st.session_state:
    st.session_state["log_accesos"] = []

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Portal Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            col_c = encontrar_columna(df_u, "CLAVE") or encontrar_columna(df_u, "PASS")
            if col_c and not df_u.empty:
                match = df_u[df_u[col_c].astype(str).str.strip() == pwd.strip()]
                if not match.empty:
                    u = match.iloc[0]
                    st.session_state["authenticated"] = True
                    st.session_state["u_nom"] = u.get('Nombre', u.get('NOMBRE', 'Usuario'))
                    st.session_state["u_rol"] = u.get('Rol', u.get('ROL', 'USUARIO'))
                    st.session_state["u_emp"] = u.get('Empresa', u.get('EMPRESA', ''))
                    st.rerun()
                else: st.error("❌ Clave incorrecta")
    st.stop()

# --- 3. DATOS ---
with st.sidebar:
    st.image("https://cysasociados.cl/wp-content/uploads/2022/05/logo-cys.png", width=150)
    st.write(f"👤 **{st.session_state['u_nom']}**")
    anio = st.selectbox("Año de Análisis", ["2026", "2025"])
    if st.button("Cerrar Sesión"):
        del st.session_state["authenticated"]
        st.rerun()

df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "Hoja 1")

# Mapa de Colores Global
mapa_txt = {1:"Carga", 2:"Revisión", 3:"Obs", 4:"No Cumple", 5:"Cumple", 8:"S/I", 9:"N/A"}
col_map = {"Carga":"#FF8C00", "Revisión":"#1E90FF", "Obs":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "S/I":"#555555", "N/A":"#8B4513"}

# --- 4. ESTRUCTURA DE 4 PESTAÑAS ---
rol = st.session_state["u_rol"]
if rol == "ADMIN":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Laboral", "⚙️ Log de Transacciones"])
elif rol == "REVISOR":
    tabs = st.tabs(["📈 Avance Laboral", "🏢 KPIs Empresas", "👥 Masa Laboral"])
else:
    tabs = st.tabs(["📈 Mi Avance", "👥 Masa Laboral"])

# --- TAB 1: AVANCE LABORAL (COMPLETO) ---
with tabs[0]:
    if not df_av.empty:
        col_emp = encontrar_columna(df_av, "EMPRESA")
        meses_ab = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic']
        cols_m = [c for c in df_av.columns if c.lower() in meses_ab]
        
        mes_sel = st.sidebar.selectbox("Mes Filtro:", ["AÑO COMPLETO"] + [m.upper() for m in cols_m])
        df_f = df_av[df_av[col_emp] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av

        st.header(f"Gestión de Cumplimiento - {anio}")
        
        # KPIs Superiores
        datos_kpi = df_f[cols_m] if mes_sel == "AÑO COMPLETO" else df_f[[mes_sel.lower()]]
        cumple_count = (datos_kpi == 5).sum().sum()
        total_v = datos_kpi.isin([1,2,3,4,5]).sum().sum()
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas Auditadas", len(df_f))
        k2.metric("Certificados OK", int(cumple_count))
        k3.metric("% Avance Real", f"{(cumple_count/total_v*100 if total_v > 0 else 0):.1f}%")

        # Conteo por Estados
        st.subheader("📊 Conteo por Estados")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("✅ Cumple", (datos_kpi == 5).sum().sum())
        c2.metric("🔵 Revisión", (datos_kpi == 2).sum().sum())
        c3.metric("🟡 Obs.", (datos_kpi == 3).sum().sum())
        c4.metric("🟠 Carga", (datos_kpi == 1).sum().sum())
        c5.metric("🔴 No Cumple", (datos_kpi == 4).sum().sum())

        st.divider()

        # Gráfico de Barras Evolución
        if rol != "USUARIO":
            st.subheader("📈 Evolución Mensual del Grupo")
            res_evo = []
            for m in cols_m:
                counts = df_f[m].value_counts()
                for k, v in counts.items():
                    if k in mapa_txt: res_evo.append({'Mes': m.upper(), 'Estado': mapa_txt[k], 'Cantidad': v})
            if res_evo:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', color_discrete_map=col_map, barmode='stack'), use_container_width=True)

        st.divider()

        # Detalle, Hallazgos y Buscador PDF
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f[col_emp].unique())) if rol != "USUARIO" else st.session_state["u_emp"]
        row_e = df_f[df_f[col_emp] == emp_sel].iloc[0]
        
        ca, cb = st.columns([2, 1])
        with ca:
            st.subheader("📝 Hallazgos de Auditoría")
            col_o = encontrar_columna(df_av, "OBS")
            st.warning(row_e[col_o] if col_o and pd.notna(row_e[col_o]) else "Sin observaciones registradas.")
            
        with cb:
            st.subheader("📄 Certificado Digital")
            if mes_sel == "AÑO COMPLETO": 
                st.info("Elija un mes para descargar.")
            else:
                # Conexión Directa a ID_Empresas
                df_id['KEY_MATCH'] = df_id[encontrar_columna(df_id, "EMPRESA")].apply(limpiar_val)
                match = df_id[df_id['KEY_MATCH'] == limpiar_val(emp_sel)]
                col_id_folder = encontrar_columna(df_id, "CARPETA")
                
                if not match.empty and col_id_folder:
                    id_f = str(match[col_id_folder].iloc[0]).strip()
                    if id_f and id_f != 'nan' and len(id_f) > 10:
                        mm = str(meses_ab.index(mes_sel.lower()) + 1).zfill(2)
                        nombre_pdf = f"Certificado.{mm}{anio}"
                        if st.button(f"🔍 Buscar Certificado {mes_sel}"):
                            with st.spinner("Buscando en Drive..."):
                                try:
                                    r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_f}")
                                    if r.text.startswith("http"):
                                        st.success("¡Encontrado!")
                                        st.link_button("📥 Descargar", r.text.strip())
                                    else: st.warning("⚠️ No disponible en esta carpeta.")
                                except: st.error("Error de conexión.")
                    else: st.error("❌ Esta empresa no tiene ID de Carpeta configurado.")
                else: st.error("❌ Empresa no encontrada en ID_Empresas.")

        # --- VOLVIÓ EL GRÁFICO CIRCULAR ---
        st.divider()
        st.subheader(f"🟢 Distribución de Estados: {emp_sel}")
        df_pie = pd.DataFrame([{'Mes': m.upper(), 'Estado': mapa_txt.get(int(row_e[m]), "S/I") if pd.notna(row_emp := row_e[m]) else "S/I"} for m in (cols_m if mes_sel=="AÑO COMPLETO" else [mes_sel.lower()])])
        st.plotly_chart(px.pie(df_pie, names='Estado', hole=.4, color='Estado', color_discrete_map=col_map), use_container_width=True)

# --- TAB 2: KPIs EMPRESAS ---
if rol != "USUARIO":
    with tabs[1]:
        st.header("🏢 Datos Maestros de Empresas")
        st.dataframe(df_id, use_container_width=True)

# --- TAB 3: MASA LABORAL ---
with (tabs[2] if rol != "USUARIO" else tabs[1]):
    st.header("👥 Gestión de Masa Laboral")
    st.info("Espacio reservado para el análisis de dotación de colaboradores.")

# --- TAB 4: LOG DE TRANSACCIONES ---
if rol == "ADMIN":
    with tabs[3]:
        st.header("⚙️ Registro de Actividad")
        st.table(pd.DataFrame(st.session_state["log_accesos"]))


# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")