import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import base64
import re
import os
from datetime import datetime
import pytz

# ==============================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y LIMPIEZA VISUAL (CSS)
# ==============================================================================
st.set_page_config(
    page_title="Control de Cumplimiento Laboral CMSG", 
    layout="wide", 
    page_icon="🛡️"
)
chile_tz = pytz.timezone('America/Santiago')

# TRUCO CSS: Oculta el mensaje nativo de "200MB" y mejora la estética de los paneles
st.markdown("""
    <style>
    /* Ocultar etiquetas de peso predeterminadas de Streamlit */
    [data-testid="stFileUploaderInstructions"] div { display: none !important; }
    .stFileUploader section div div { display: none !important; }
    .stFileUploader section div { padding-top: 5px !important; }
    /* Estética para cuadros de instrucciones */
    .caja-instrucciones {
        background-color: #fefefe; 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #ddd;
        margin-bottom: 15px;
    }
    .stButton > button { width: 100%; border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# URL DE CONEXIÓN CON GOOGLE DRIVE (APPS SCRIPT)
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbwt9t5vQBsijY4eI9yF-sI82ctU5HGuW8xE2WVPwUBjOvaqGSGh7bi1DZaazU7NQEavfA/exec"

# IDS DE LAS HOJAS DE CÁLCULO (BASE DE DATOS)
ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# LISTA MAESTRA DE CAUSALES DE FINIQUITO (CHILE)
CAUSALES_LEGALES = [
    "Art. 159 N°1: Mutuo acuerdo de las partes",
    "Art. 159 N°2: Renuncia voluntaria del trabajador",
    "Art. 159 N°3: Muerte del trabajador",
    "Art. 159 N°4: Vencimiento del plazo convenido",
    "Art. 159 N°5: Conclusión del trabajo o servicio",
    "Art. 159 N°6: Caso fortuito o fuerza mayor",
    "Art. 160: Conductas indebidas de carácter grave",
    "Art. 161: Necesidades de la empresa",
    "Traslado de Faena / Anexo de Contrato"
]

# MAPEOS VISUALES Y CORPORATIVOS
MAPA_ESTADOS = {1: "Carga Doc.", 2: "En Revision", 3: "Observado", 4: "No Cumple", 5: "Cumple", 8: "Sin Info", 9: "No Corresp."}
COLORES_ESTADOS = {"Cumple": "#00FF00", "No Cumple": "#FF0000", "Observado": "#FFFF00", "En Revision": "#1E90FF", "Carga Doc.": "#FF8C00", "Sin Info": "#555555", "No Corresp.": "#8B4513"}
MESES_LISTA = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARP = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

# ==============================================================================
# 2. FUNCIONES DE VALIDACIÓN Y CARGA
# ==============================================================================
def validar_rut(rut):
    """Verifica si el RUT chileno es matemáticamente correcto."""
    rut = str(rut).replace(".", "").replace("-", "").upper()
    if not re.match(r"^\d{7,8}[0-9K]$", rut): return False
    cuerpo, dv = rut[:-1], rut[-1]
    suma = 0; multiplo = 2
    for c in reversed(cuerpo):
        suma += int(c) * multiplo
        multiplo = 2 if multiplo == 7 else multiplo + 1
    dvr = 11 - (suma % 11)
    dvr = 'K' if dvr == 10 else '0' if dvr == 11 else str(dvr)
    return dv == dvr

@st.cache_data(ttl=15)
def cargar_datos(sheet_id, p):
    """Lee datos desde Google Sheets vía CSV."""
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={p}"
        df = pd.read_csv(url, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# ==============================================================================
# 3. SISTEMA DE LOGIN (FIX VARIABLE NAMEERROR)
# ==============================================================================
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        if os.path.exists("CMSG.png"): st.image("CMSG.png", width=220)
        st.title("Control de Cumplimiento CMSG")
        pwd = st.text_input("Contraseña Corporativa:", type="password").strip()
        if st.button("Ingresar al Portal", use_container_width=True):
            df_u = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_u.empty:
                # SE CORRIGE: Se busca la columna de clave de forma dinámica
                col_c_login = next((c for c in df_u.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                match = df_u[df_u[col_c_login].astype(str).str.strip() == pwd]
                if not match.empty:
                    u = match.iloc[0]
                    st.success(f"Bienvenido(a), {u.get('NOMBRE','')}")
                    st.session_state.update({
                        "authenticated": True, 
                        "u_nom": u.get('NOMBRE',''), 
                        "u_rol": u.get('ROL',''), 
                        "u_emp": u.get('EMPRESA',''), 
                        "u_email": u.get('EMAIL','')
                    })
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
    st.stop()

# ==============================================================================
# 4. SIDEBAR Y PERMISOS DE PESTAÑAS (EECC SOLO VE 1, 3 Y 4)
# ==============================================================================
with st.sidebar:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", use_container_width=True)
    st.markdown(f"👤 **{st.session_state['u_nom']}**\n🏢 **{st.session_state['u_emp']}**")
    st.markdown("---")
    anio_global = st.selectbox("Año de Gestión", ["2026", "2025"])
    df_av = cargar_datos(ID_AVANCE, anio_global)
    cols_m = [c for c in df_av.columns if c in MESES_LISTA] if not df_av.empty else []
    mes_sidebar = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m)
    if st.button("🚪 Cerrar Sesión"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

rol = st.session_state["u_rol"]

# FILTRO DE PESTAÑAS PARA EECC
if rol == "USUARIO":
    tab_list = ["📈 Dashboard", "📤 Carga Mensual", "👥 DOTACION"]
else:
    tab_list = ["📈 Dashboard", "📊 KPIS EMPRESAS", "📤 Carga Mensual", "👥 DOTACION", "⚙️ Admin"]

tabs = st.tabs(tab_list)

# ==============================================================================
# 5. CONTENIDO DE PESTAÑAS (EXPANDIDO)
# ==============================================================================

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    df_id_empresas = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av.empty:
        col_e = next((c for c in df_av.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        df_f = df_av[df_av[col_e] == st.session_state["u_emp"]] if rol == "USUARIO" else df_av
        c_filt = [mes_sidebar] if mes_sidebar != "AÑO COMPLETO" else cols_m
        
        df_num = df_f[c_filt].apply(pd.to_numeric, errors='coerce')
        df_audit = df_num.copy(); df_audit[df_audit == 9] = pd.NA
        t_p = df_audit.count().sum(); t_5 = (df_audit == 5).sum().sum()
        perc = (t_5 / t_p * 100) if t_p > 0 else 0
        
        st.header(f"Seguimiento - {mes_sidebar} {anio_global}")
        k1, k2, k3 = st.columns(3)
        k1.metric("Empresas", len(df_f))
        k2.metric("% Cumplimiento", f"{perc:.1f}%")
        k3.metric("Al Día", int(t_5))

        if mes_sidebar == "AÑO COMPLETO":
            st.divider(); st.write("### 📈 Evolución Mensual")
            res_evo = []
            for m in cols_m:
                counts_m = df_f[m].value_counts()
                for cod, cant in counts_m.items():
                    if pd.notna(cod): res_evo.append({'Mes': m, 'Estado': MAPA_ESTADOS.get(int(cod), "S/I"), 'Cantidad': cant})
            if res_evo: st.plotly_chart(px.bar(pd.DataFrame(res_evo), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider(); emp_sel = st.selectbox("Empresa para Detalle:", sorted(df_f[col_e].unique()))
        df_es = df_f[df_f[col_e] == emp_sel]
        c_iz, c_de = st.columns([3, 1.2])
        with c_iz:
            p_d = df_es[cols_m].stack().value_counts().reset_index(); p_d.columns = ['Cod', 'Cant']; p_d['Estado'] = p_d['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(p_d[p_d['Cod'] != 9], values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS), use_container_width=True)
            st.write("#### 📜 Historial Mensual"); m1, m2 = cols_m[:6], cols_m[6:]
            def draw_grid_c(l):
                cs = st.columns(6)
                for i, m in enumerate(l):
                    v = int(df_es[m].values[0]) if pd.notna(df_es[m].values[0]) else 8
                    t = MAPA_ESTADOS.get(v, "S/I"); b = COLORES_ESTADOS.get(t, "#555555"); tc = "#000000" if t in ["Observado", "Cumple", "En Revision"] else "#FFFFFF"
                    cs[i].markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:8px; border-radius:8px; background-color:{b}; color:{tc}; min-height:65px; display:flex; flex-direction:column; justify-content:center;'><b style='font-size:11px;'>{m}</b><br><span style='font-size:8px; font-weight:bold;'>{t.upper()}</span></div>", unsafe_allow_html=True)
            draw_grid_c(m1); st.write(""); draw_grid_c(m2)
        with c_de:
            st.subheader("📄 Certificado")
            m_pdf = st.selectbox("Mes PDF:", cols_m, key="s_pdf_dash")
            if st.button("Obtener Link", use_container_width=True):
                match_id = df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_sel[:10], case=False, na=False)]
                if not match_id.empty:
                    id_f = str(match_id.iloc[0]['IDCARPETA']).strip(); n_f = f"Certificado.{MAPA_MESES_NUM[m_pdf]}{anio_global}.pdf"
                    r = requests.get(URL_APPS_SCRIPT, params={"nombre": n_f, "carpeta": id_f})
                    if r.text.startswith("http"): st.session_state["link_desc"] = r.text.strip()
            if "link_desc" in st.session_state: st.link_button("📥 Descargar PDF", st.session_state["link_desc"], use_container_width=True)

# --- TAB: KPIS EMPRESAS (SOLO ADMIN) ---
if rol != "USUARIO":
    with tabs[tab_list.index("📊 KPIS EMPRESAS")]:
        st.header(f"📊 Dotación Vigente - {anio_global}")
        mes_kpi = st.selectbox("Visualizar Mes:", MESES_LISTA, key="m_kpi_v")
        df_k = cargar_datos(ID_COLABORADORES, f"{mes_kpi.capitalize()}{anio_global[-2:]}")
        if not df_k.empty: st.dataframe(df_k, use_container_width=True)

# --- TAB: CARGA MENSUAL ---
with tabs[tab_list.index("📤 Carga Mensual")]:
    st.header("📤 Carga Documental Mensual")
    if mes_sidebar == "AÑO COMPLETO": st.warning("Seleccione un Mes en el sidebar para cargar.")
    else:
        col_m_inp, col_m_inst = st.columns([1.7, 1.3])
        with col_m_inst:
            st.markdown("""<div class='caja-instrucciones' style='border-left: 8px solid #FF8C00;'><h4>📖 Instrucciones</h4><p style='color:#d9534f;'><b>⚠️ MÁXIMO 20MB POR ARCHIVO.</b></p><ul><li>Liquidaciones (PDF único)</li><li>Libro Remuneraciones (CSV)</li><li>F30 / F30-1 Vigentes</li><li>Planilla Control (.XLS)</li></ul></div>""", unsafe_allow_html=True)
        with col_m_inp:
            emp_u = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("Empresa:", sorted(df_av[col_e].unique()), key="up_m_sel")
            st.divider()
            # LISTADO EXPLÍCITO DE DOCUMENTOS
            docs_mensuales = [
                ("Liquidaciones Sueldo", "LIQ", ["pdf"]),
                ("Comprobantes Pago", "PAGOS", ["pdf"]),
                ("Cotizaciones", "PREV", ["pdf"]),
                ("Libro Remuneraciones", "LIBRO", ["csv"]),
                ("Comprobante DT", "DT_COMP", ["pdf"]),
                ("Certificado F30", "F30", ["pdf"]),
                ("Certificado F30-1", "F30_1", ["pdf"]),
                ("Planilla Control (.XLS)", "CONTROL", ["xlsx", "xls"])
            ]
            for n, p, e in docs_mensuales:
                cf, cb, cs = st.columns([4, 2, 0.5])
                with cf: a = st.file_uploader(f"Subir {n} (Máx 20MB)", type=e, key=f"m_{p}")
                with cb:
                    st.write("##")
                    if st.button("Subir", key=f"bm_{p}", use_container_width=True):
                        if a and a.size <= 20*1024*1024:
                            id_f = str(df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_u[:10], case=False, na=False)].iloc[0]['IDCARPETA']).strip()
                            requests.post(URL_APPS_SCRIPT, data={"tipo":"mensual","id_carpeta":id_f,"anio":anio_global,"nombre_final":f"{p}_{mes_sidebar}.{a.name.split('.')[-1]}","archivo_base64":base64.b64encode(a.read()).decode('utf-8')})
                            st.success("Cargado.")
                        elif a: st.error("⚠️ Excede 20MB.")
            st.divider()
            if st.button("🏁 FINALIZAR Y NOTIFICAR", key="btn_notif_mensual_final", use_container_width=True):
                requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email","empresa":emp_u,"usuario":st.session_state["u_nom"],"periodo":f"Periodo Mensual: {mes_sidebar} {anio_global}"})
                st.success("Notificado.")

# --- TAB: DOTACION (GESTIÓN DE ALTAS Y BAJAS CON CAUSAL) ---
with tabs[tab_list.index("👥 DOTACION")]:
    st.header("👥 Gestión de Movimientos de Personal")
    acc = st.radio("Acción:", ["🟢 Alta (Ingreso)", "🔴 Baja (Egreso/Traslado)"], horizontal=True)
    st.divider()
    col_d_inp, col_d_inst = st.columns([1.7, 1.3])
    with col_d_inst:
        color_b = "#1E90FF" if "Alta" in acc else "#d9534f"
        txt_d = "<li>Documentos firmados</li><li>Fecha exacta movimiento</li><li>Causal legal (en Bajas)</li>"
        st.markdown(f"""<div class='caja-instrucciones' style='border-left: 8px solid {color_b};'><h4>📌 Información Requerida</h4><p style='color:#d9534f;'><b>⚠️ MÁXIMO 20MB POR ARCHIVO.</b></p><ul>{txt_d}</ul></div>""", unsafe_allow_html=True)
    with col_d_inp:
        emp_c = st.session_state['u_emp'] if rol == "USUARIO" else st.selectbox("EECC:", sorted(df_av[col_e].unique()), key="c_up_dot")
        c1, c2 = st.columns(2)
        with c1: n_nom = st.text_input("Nombre Trabajador:", placeholder="Nombre Apellido")
        with c2: 
            r_rut = st.text_input("RUT Trabajador:", placeholder="12.345.678-9")
            r_ok = validar_rut(r_rut) if r_rut else False
            if r_rut: st.caption("✅ RUT Válido" if r_ok else "❌ RUT Inválido")
        
        # NUEVOS CAMPOS DE GESTIÓN RRHH
        c3, c4 = st.columns(2)
        with c3: f_mov = st.date_input("Fecha del Movimiento:", datetime.now())
        with c4:
            if "Baja" in acc: cau_mov = st.selectbox("Causal Legal:", CAUSALES_LEGALES)
            else: cau_mov = "Nuevo Ingreso (Alta)"

        st.divider()
        f_up = st.file_uploader("Documentación (Máx 20MB):", type=["pdf"], accept_multiple_files=True, key="bulk_in")
        
        if st.button("🚀 FINALIZAR Y NOTIFICAR", key="btn_notif_dot_final", use_container_width=True):
            if n_nom and r_ok and f_up:
                id_f = str(df_id_empresas[df_id_empresas['EMPRESA'].str.contains(emp_c[:10], case=False, na=False)].iloc[0]['IDCARPETA']).strip()
                for f in f_up:
                    requests.post(URL_APPS_SCRIPT, data={"tipo":"colaborador","id_carpeta":id_f,"nombre_persona":n_nom.upper(),"rut":r_rut,"nombre_final":f.name,"archivo_base64":base64.b64encode(f.read()).decode('utf-8')})
                
                # ENVÍO DE EMAIL LIMPIO SIN LA PALABRA PERIODO EN EL TEXTO
                # Se envía a la llave 'periodo' para compatibilidad con el Script, pero el texto es dinámico
                detalle_notif = f"Acción: {acc}\nTrabajador: {n_nom.upper()}\nFecha Evento: {f_mov.strftime('%d/%m/%Y')}\nCausal: {cau_mov}"
                requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email", "empresa":emp_c, "usuario":st.session_state["u_nom"], "periodo": detalle_notif})
                st.success(f"✅ Notificado: {acc} de {n_nom.upper()}")
            else: st.warning("Complete todos los campos y cargue los archivos.")

# --- TAB: ADMIN ---
if rol != "USUARIO":
    with tabs[tab_list.index("⚙️ Admin")]:
        st.header("⚙️ Configuración Administrativa")
        st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("Control Laboral CMSG | Desarrollado por C & S Asociados Ltda.")