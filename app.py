import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
import re

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="Control Laboral CMSG", layout="wide", page_icon="🛡️")
st.markdown("<style>#MainMenu {visibility: hidden;} footer {visibility: hidden;}</style>", unsafe_allow_html=True)

URL_MI_SCRIPT = "https://script.google.com/a/macros/cysasociados.cl/s/AKfycbwi-UFcqZPZFmvA_80Naul4hHoJJAgUd8htMkJUmCpnGs_BAweZVOFFzclWQczMQXbq/exec"

# IDs de Google Sheets
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"

# --- FUNCIONES DE LIMPIEZA INTELIGENTE ---
def normalizar_nombre(t):
    if pd.isna(t): return ""
    return re.sub(r'[^A-Z0-9]', '', str(t).upper().strip())

def limpiar_col(c):
    # Convierte "Obs Auditoria" o "ene" en "OBS_AUDITORIA" o "ENE"
    return re.sub(r'[^A-Z0-9]', '_', str(c).upper().strip())

@st.cache_data(ttl=30)
def cargar_datos(sheet_id, nombre_pestana):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
        df = pd.read_csv(url)
        df.columns = [limpiar_col(c) for c in df.columns]
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- 2. LOGIN ---
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🔐 Acceso Control Laboral CMSG")
        pwd = st.text_input("Contraseña:", type="password")
        if st.button("Ingresar"):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                col_c = next((c for c in df_u.columns if "CLAVE" in c or "PASS" in c), None)
                if col_c:
                    match = df_u[df_u[col_c].astype(str).str.strip() == pwd.strip()]
                    if not match.empty:
                        u = match.iloc[0]
                        st.session_state["authenticated"] = True
                        st.session_state["u_nom"] = u.get('NOMBRE', 'Usuario')
                        st.session_state["u_rol"] = u.get('ROL', 'USUARIO')
                        st.session_state["u_emp"] = u.get('EMPRESA', '')
                        st.rerun()
                    else: st.error("❌ Clave incorrecta")
    st.stop()

# --- 3. CARGA DE DATOS ---
anio = st.sidebar.selectbox("Año de Análisis", ["2026", "2025"])
df_av = cargar_datos(ID_AVANCE, anio)
df_id = cargar_datos(ID_EMPRESAS, "Hoja 1")

if df_av.empty:
    st.error(f"⚠️ No se encontraron datos en la pestaña '{anio}'.")
    st.stop()

# --- 4. DETECCIÓN DINÁMICA DE MESES ---
meses_posibles = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
cols_m = [c for c in df_av.columns if any(m == c for m in meses_posibles)]

# --- 5. INTERFAZ PRINCIPAL ---
st.sidebar.write(f"👤 **{st.session_state['u_nom']}**")
if st.sidebar.button("Cerrar Sesión"):
    del st.session_state["authenticated"]
    st.rerun()

# Filtro por empresa
df_f = df_av[df_av['EMPRESA'] == st.session_state["u_emp"]] if st.session_state["u_rol"] == "USUARIO" else df_av

t1, t2 = st.tabs(["📈 Avance y Reportes", "⚙️ Admin & Diagnóstico"])

with t1:
    mes_sel = st.sidebar.selectbox("Seleccione Mes:", ["AÑO COMPLETO"] + cols_m)
    st.header(f"Gestión de Cumplimiento - {anio}")
    
    # KPIs
    datos_kpi = df_f[cols_m if mes_sel == "AÑO COMPLETO" else [mes_sel]]
    c1, c2, c3 = st.columns(3)
    c1.metric("Empresas Auditadas", len(df_f))
    cumple = (datos_kpi == 5).sum().sum()
    total_val = datos_kpi.isin([1,2,3,4,5]).sum().sum()
    c2.metric("Certificados OK", int(cumple))
    c3.metric("% Cumplimiento", f"{(cumple/total_val*100 if total_val>0 else 0):.1f}%")

    st.divider()

    # BUSCADOR Y DETALLE
    if not df_f.empty:
        emp_sel = st.selectbox("Seleccione Empresa:", sorted(df_f['EMPRESA'].unique())) if st.session_state["u_rol"] != "USUARIO" else st.session_state["u_emp"]
        row = df_f[df_f['EMPRESA'] == emp_sel].iloc[0]
        
        col_obs, col_pdf = st.columns([2, 1])
        with col_obs:
            st.subheader("📝 Hallazgos de Auditoría")
            # Buscamos la columna de observaciones (flexible)
            col_o = next((c for c in df_av.columns if "OBS" in c), None)
            if col_o and col_o in row and pd.notna(row[col_o]):
                st.warning(row[col_o])
            else:
                st.success("✅ Sin observaciones pendientes o datos cargados.")
            
        with col_pdf:
            st.subheader("📄 Certificado Digital")
            if mes_sel == "AÑO COMPLETO":
                st.info("Seleccione un mes en el menú lateral.")
            else:
                # Match con ID_Empresas
                if not df_id.empty:
                    df_id['MATCH_KEY'] = df_id['EMPRESA'].apply(normalizar_nombre)
                    match = df_id[df_id['MATCH_KEY'] == normalizar_nombre(emp_sel)]
                    col_id = next((c for c in df_id.columns if "CARPETA" in c or "ID" in c), None)
                    
                    if not match.empty and col_id:
                        id_f = str(match[col_id].iloc[0]).strip()
                        if id_f and id_f != "nan":
                            num_mes = str(meses_posibles.index(mes_sel) + 1).zfill(2)
                            nombre_pdf = f"Certificado.{num_mes}{anio}"
                            
                            if st.button(f"🔍 Buscar Certificado {mes_sel}"):
                                r = requests.get(f"{URL_MI_SCRIPT}?nombre={nombre_pdf}&carpeta={id_f}", timeout=10)
                                if r.text.startswith("http"):
                                    st.success("¡Encontrado!")
                                    st.link_button("📥 Descargar PDF", r.text.strip())
                                else: st.warning("⚠️ Certificado No Disponible")
                        else: st.error("Esta empresa no tiene ID de Carpeta configurado.")
                    else: st.error("Empresa no vinculada en la base de IDs.")

        # Gráfico
        st.divider()
        mapa = {1:"Carga", 2:"Revisión", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"S/I", 9:"N/A"}
        colores = {"Carga":"#FF8C00", "Revisión":"#1E90FF", "Observado":"#FFFF00", "No Cumple":"#FF0000", "Cumple":"#00FF00", "S/I":"#555555", "N/A":"#8B4513"}
        
        df_p = pd.DataFrame([{'Mes': m, 'Estado': mapa.get(int(row[m]), "S/I") if pd.notna(row[m]) else "S/I"} for m in (cols_m if mes_sel=="AÑO COMPLETO" else [mes_sel])])
        st.plotly_chart(px.pie(df_p, names='Estado', hole=.4, color='Estado', color_discrete_map=colores), use_container_width=True)
    else:
        st.info("No hay datos para mostrar.")

with t2:
    st.subheader("🛠️ Diagnóstico del Sistema")
    st.write("Columnas detectadas en Avance:", df_av.columns.tolist())
    st.write("Columnas detectadas en Empresas:", df_id.columns.tolist())
    st.dataframe(df_av.head(10))

# Pie de página
st.markdown("---")
st.caption("Sistema de gestión de datos en tiempo real, desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")