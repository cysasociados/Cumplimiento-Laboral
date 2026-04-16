¡Entendido, Sergio! Tienes razón, 350 era demasiado protagonismo para la pantalla de entrada. Lo he ajustado a 220, que es el tamaño estándar que veníamos usando en la cabecera interna y que mantiene la elegancia sin saturar la vista.

Aquí tienes el código completo con el ajuste del tamaño del logo en el login y manteniendo todas las funciones de "hospitalidad" y visuales que ya te gustaron.

🐍 app.py: Versión Final con Logo Ajustado
Python
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# 1. CONFIGURACION
st.set_page_config(page_title="Control de Cumplimiento Laboral CMSG", layout="wide", page_icon="🛡️")
chile_tz = pytz.timezone('America/Santiago')

# CONEXION
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbxuGe9TQYwyKDHPaKJKiR8XqD14Uk7s8vk9BksMCGNBJb-0BZFj8ztWek9pJ3nDkXIBtQ/exec"
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

MAPA_ESTADOS = {1:"Carga Doc.", 2:"En Revision", 3:"Observado", 4:"No Cumple", 5:"Cumple", 8:"Sin Info", 9:"No Corresp."}
COLORES_ESTADOS = {"Cumple":"#00FF00", "No Cumple":"#FF0000", "Observado":"#FFFF00", "En Revision":"#1E90FF", "Carga Doc.":"#FF8C00", "Sin Info":"#555555", "No Corresp.":"#8B4513"}
MESES_LISTA = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, p):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={p}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# 2. LOGIN (CON LOGO AJUSTADO Y SALUDO)
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # Logo en Pantalla de Inicio (Tamaño reducido a 220)
        if os.path.exists("CMSG.png"):
            st.image("CMSG.png", width=220)
        
        st.title("Acceso a Control Laboral de CMSG")
        pwd = st.text_input("Ingrese su contraseña de acceso:", type="password").strip()
        
        if st.button("Ingresar", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                col_c = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                df_u[col_c] = df_u[col_c].astype(str).str.strip()
                match = df_u[df_u[col_c] == pwd]
                if not match.empty:
                    u = match.iloc[0]
                    nombre_u = u.get('NOMBRE','')
                    st.success(f"✅ ¡Bienvenido(a), {nombre_u}! Accediendo...")
                    
                    st.session_state.update({
                        "authenticated": True, 
                        "u_nom": nombre_u, 
                        "u_rol": u.get('ROL',''), 
                        "u_emp": u.get('EMPRESA',''), 
                        "u_email": u.get('EMAIL','')
                    })
                    st.rerun()
                else: st.error("❌ Clave incorrecta.")
    st.stop()

# 3. SIDEBAR (PERFIL Y FILTROS)
with st.sidebar:
    if os.path.exists("CMSG.png"):
        st.image("CMSG.png", use_container_width=True)
    
    st.markdown("---")
    st.markdown(f"👤 **Usuario:** {st.session_state['u_nom']}")
    st.markdown(f"🏢 **Empresa:** {st.session_state['u_emp']}")
    st.markdown(f"🔑 **Rol:** {st.session_state['u_rol']}")
    st.markdown("---")
    
    st.header("Seleccione Periodo")
    anio_global = st.selectbox("Año", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MESES_LISTA] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# --- CABECERA INTERNA ---
col_logo_in, col_vacio = st.columns([1, 4])
with col_logo_in:
    if os.path.exists("CMSG.png"):
        st.image("CMSG.png", width=220)

# 4. TABS
rol = st.session_state["u_rol"]
tab_list = ["📈 Mi Avance", "👥 Dotacion", "📤 Carga Doc"] if rol == "USUARIO" else ["📈 Avance Global", "🏢 Empresas", "👥 Dotacion", "📤 Carga Doc", "⚙️ Admin"]
tabs = st.tabs(tab_list)

# TAB 1: DASHBOARD
with tabs[0]:
    df_id_empresas = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        c_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        df_num = df_f[c_filt].apply(pd.to_numeric, errors='coerce')

        # MATEMATICA SIN ESTADO 9
        df_audit = df_num.copy()
        df_audit[df_audit == 9] = pd.NA
        t_p = df_audit.count().sum()
        t_5 = (df_audit == 5).sum().sum()
        perc = (t_5 / t_p * 100) if t_p > 0 else 0

        if mes_sidebar == "AÑO COMPLETO":
            al_dia = df_audit.apply(lambda x: x.dropna().eq(5).all() if x.dropna().size > 0 else False, axis=1).sum()
        else: al_dia = (df_audit == 5).sum().sum()

        st.header(f"Seguimiento Control Laboral - {mes_sidebar} {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas en Panel", len(df_f))
        k2.metric("% Cumplimiento Real", f"{perc:.1f}%")
        k3.metric("Empresas 100% Al Día", int(al_dia))

        # Recuento de Estados
        st.write("###")
        st_c = df_num.stack().value_counts()
        m_cols_res = st.columns(len(MAPA_ESTADOS))
        for i, (code, name) in enumerate(MAPA_ESTADOS.items()):
            m_cols_res[i].metric(name, int(st_c.get(code, 0)))

        # GRAFICO BARRAS EVOLUTIVO
        if mes_sidebar == "AÑO COMPLETO":
            st.divider()
            st.write("### 📈 Evolución Mensual Estados de Cumplimiento")
            res_evo = []
            for m in cols_m:
                counts_m = df_f[m].value_counts()
                for cod, cant in counts_m.items():
                    if pd.notna(cod):
                        res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider()
        emp_sel = st.selectbox("Seleccione Empresa para Detalle:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        row_sel = df_es.iloc[0]

        # LAYOUT VISUAL
        col_izq, col_der = st.columns([3, 1.2])

        with col_izq:
            # Gráfico Circular
            p_d = df_es[cols_m].stack().value_counts().reset_index()
            p_d.columns = ['Cod', 'Cant']; p_d['Estado'] = p_d['Cod'].map(MAPA_ESTADOS)
            p_final = p_d[p_d['Cod'] != 9]
            st.plotly_chart(px.pie(p_final, values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Distribución de Cumplimiento: {emp_sel}"), use_container_width=True)
            
            # HISTORIAL CROMÁTICO
            st.write("#### 📜 Historial Mensual")
            m1, m2 = cols_m[:6], cols_m[6:]
            
            def dibujar_grid(lista):
                cols = st.columns(6)
                for i, m in enumerate(lista):
                    v_val = df_es[m].values[0]
                    v = int(v_val) if pd.notna(v_val) else 8
                    t = MAPA_ESTADOS.get(v, "Sin Info")
                    b = COLORES_ESTADOS.get(t, "#555555")
                    c = "#000000" if t in ["Observado", "Cumple", "En Revision"] else "#FFFFFF"
                    
                    cols[i].markdown(f"""
                        <div style='text-align:center; border:1px solid #ddd; padding:8px; border-radius:8px; 
                        background-color:{b}; color:{c}; min-height:65px; display:flex; flex-direction:column; justify-content:center;'>
                        <b style='font-size:13px;'>{m}</b><br><span style='font-size:9px; font-weight:bold;'>{t.upper()}</span>
                        </div>
                    """, unsafe_allow_html=True)

            dibujar_grid(m1)
            st.write("")
            dibujar_grid(m2)

        with col_der:
            st.subheader("📄 Certificado")
            m_pdf_sel = st.selectbox("Mes para PDF:", cols_m, key="sel_pdf")
            
            if "last_selection" not in st.session_state or st.session_state["last_selection"] != f"{emp_sel}_{m_pdf_sel}":
                st.session_state["last_selection"] = f"{emp_sel}_{m_pdf_sel}"
                if "link_descarga" in st.session_state: del st.session_state["link_descarga"]

            if st.button("🔍 Obtener y Descargar Certificado", use_container_width=True):
                match_id = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_sel[:10], case=False, na=False)]
                if not match_id.empty:
                    id_f = str(match_id.iloc[0]['IDCARPETA']).strip()
                    mm = MAPA_MESES_NUM[m_pdf_sel]
                    n_f = f"Certificado.{mm}{anio_global}.pdf"
                    
                    with st.spinner("Buscando..."):
                        try:
                            r = requests.get(URL_APPS_SCRIPT, params={"nombre": n_f, "carpeta": id_f}, timeout=15)
                            if r.text.startswith("http"):
                                st.session_state["link_descarga"] = r.text.strip()
                            else: st.error("No se encontró el archivo.")
                        except: st.error("Error de conexión.")

            if "link_descarga" in st.session_state:
                st.success("¡Archivo listo!")
                st.link_button("📥 ABRIR / DESCARGAR PDF", st.session_state["link_descarga"], use_container_width=True)

            st.divider()
            st.subheader("📝 Observaciones")
            col_o = next((c for c in df_av.columns if 'OBS' in str(c).upper()), None)
            if col_o and pd.notna(row_sel[col_o]): st.warning(row_sel[col_o])
            else: st.info("Sin observaciones.")

# TABS ADICIONALES (DOTACION Y CARGA)
with tabs[tab_list.index("👥 Dotacion")]:
    st.header(f"Nómina de Personal - {anio_global}")
    mes_dot = st.selectbox("Filtrar Mes:", MESES_LISTA, key="m_masa")
    df_m = cargar_datos(ID_COLABORADORES, f"{mes_dot.capitalize()}{anio_global[-2:]}")
    if not df_m.empty:
        c_rs = next((c for c in df_m.columns if 'RAZON' in str(c).upper()), df_m.columns[0])
        st.dataframe(df_m[df_m[c_rs] == st.session_state["u_emp"]] if rol == "USUARIO" else df_m, use_container_width=True)

with tabs[tab_list.index("📤 Carga Doc")]:
    st.header("Pasarela de Carga de Documentación")
    if mes_sidebar == "AÑO COMPLETO": st.warning("Seleccione un mes específico.")
    else:
        emp_u = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa Destino:", sorted(df_av[col_e].unique()))
        docs = [("Liquidaciones", "LIQ"), ("Previred", "PREVIRED"), ("F30", "F30"), ("F30-1", "F30_1"), ("Pagos", "PAGOS")]
        for n, p in docs:
            c1, c2 = st.columns([3, 1])
            arch = c1.file_uploader(f"Subir {n}", type=["pdf"], key=f"u_{p}")
            if c2.button(f"Cargar {p}", key=f"b_{p}"):
                if arch:
                    mt = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_u[:10], case=False, na=False)]
                    if not mt.empty:
                        id_f_u = str(mt.iloc[0]['IDCARPETA']).strip()
                        payload = {"nombre_final": f"{p}_{mes_sidebar}_{anio_global}_{emp_u[:10]}.pdf", "id_carpeta": id_f_u, "anio": anio_global, "mes_nombre": f"{(MESES_LISTA.index(mes_sidebar)+1):02d}_{mes_sidebar}", "mimetype": "application/pdf", "archivo_base64": base64.b64encode(arch.read()).decode('utf-8')}
                        r = requests.post(URL_APPS_SCRIPT, data=payload)
                        if "Exito" in r.text: st.success("¡Cargado!"); st.balloons()
        st.divider()
        if st.button("🏁 Finalizar y Notificar"):
            p_e = {"accion": "enviar_email", "empresa": emp_u, "usuario": st.session_state["u_nom"], "periodo": f"{mes_sidebar} {anio_global}", "email_usuario": st.session_state["u_email"]}
            r = requests.post(URL_APPS_SCRIPT, data=p_e)
            if "Exito" in r.text: st.success("Notificación Enviada")

st.markdown("---")
st.caption("Sistema desarrollado por C & S Asociados Ltda. para Control Laboral CMSG")