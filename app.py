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
# 1. CONFIGURACIÓN CORPORATIVA Y ESTILOS CSS
# ==============================================================================
st.set_page_config(
    page_title="Gestión de Cumplimiento Laboral CMSG", 
    layout="wide", 
    page_icon="🛡️"
)
chile_tz = pytz.timezone('America/Santiago')

# CSS: Ocultamos los 200MB nativos y profesionalizamos la interfaz
st.markdown("""
    <style>
    /* Ocultar etiquetas de peso predeterminadas de Streamlit */
    [data-testid="stFileUploaderInstructions"] div { display: none !important; }
    .stFileUploader section div div { display: none !important; }
    .stFileUploader section div { padding-top: 5px !important; }
    
    /* Contenedores de información */
    .caja-instrucciones {
        background-color: #f8f9fa; 
        padding: 22px; 
        border-radius: 15px; 
        border: 1px solid #dee2e6;
        margin-bottom: 20px;
    }
    
    /* Botones de gran formato */
    .stButton > button { 
        width: 100%; 
        border-radius: 12px; 
        font-weight: bold; 
        height: 3.8em;
        transition: 0.3s;
    }
    
    /* Resaltado de métricas */
    [data-testid="stMetricValue"] { 
        font-size: 35px; 
        color: #1E90FF; 
        font-weight: 800; 
    }
    </style>
    """, unsafe_allow_html=True)

# CONEXIONES TÉCNICAS
URL_APPS_SCRIPT = "https://script.google.com/macros/s/AKfycbwt9t5vQBsijY4eI9yF-sI82ctU5HGuW8xE2WVPwUBjOvaqGSGh7bi1DZaazU7NQEavfA/exec"

ID_AVANCE = "1H-L5zzWlm1_bubJab3G_kztzWBfgUZuPnFvrbcFvj7Y"
ID_EMPRESAS = "1sC0BNZTc1UuOVhl9UqaBqCehuXso3AxqBVwQ7tm4Ybo" 
ID_USUARIOS = "1FnjiFO_m2h1BqlzNFnR5AQhBY8924MrAg-QP8oZV7CY"
ID_COLABORADORES = "1EAJF1P2W2cFkl-QvD6RwTpms-_R_aYeabDZxIyOB4W0"

# CAUSALES DE EGRESO
CAUSALES_FINIQUITO = [
    "Art. 159 N°1: Mutuo acuerdo de las partes",
    "Art. 159 N°2: Renuncia voluntaria del trabajador",
    "Art. 159 N°4: Vencimiento del plazo convenido",
    "Art. 159 N°5: Conclusión del trabajo o servicio",
    "Art. 160: Conductas indebidas de carácter grave",
    "Art. 161: Necesidades de la empresa",
    "Traslado de Faena / Anexo de Contrato"
]

# MAPEOS DE ESTADOS (7 ESTADOS)
MAPA_ESTADOS = {
    1: "Carga Doc.", 
    2: "En Revision", 
    3: "Observado", 
    4: "No Cumple", 
    5: "Cumple", 
    8: "Sin Info", 
    9: "No Corresp."
}

COLORES_ESTADOS = {
    "Cumple": "#00FF00", 
    "No Cumple": "#FF0000", 
    "Observado": "#FFFF00", 
    "En Revision": "#1E90FF", 
    "Carga Doc.": "#FF8C00", 
    "Sin Info": "#555555", 
    "No Corresp.": "#8B4513"
}

MESES_LISTA = ['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC']
MAPA_MESES_NUM = {'ENE':'01','FEB':'02','MAR':'03','ABR':'04','MAY':'05','JUN':'06','JUL':'07','AGO':'08','SEP':'09','OCT':'10','NOV':'11','DIC':'12'}
MAPA_MESES_CARP = {'ENE':'01_ENE','FEB':'02_FEB','MAR':'03_MAR','ABR':'04_ABR','MAY':'05_MAY','JUN':'06_JUN','JUL':'07_JUL','AGO':'08_AGO','SEP':'09_SEP','OCT':'10_OCT','NOV':'11_NOV','DIC':'12_DIC'}

# ==============================================================================
# 2. FUNCIONES DE VALIDACIÓN Y CARGA
# ==============================================================================
def validar_rut(rut):
    """Algoritmo Módulo 11 para RUT chileno."""
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

@st.cache_data(ttl=10)
def cargar_datos(sheet_id, hoja):
    """Cargador de datos CSV robusto y explícito."""
    try:
        url_csv = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={hoja}"
        df = pd.read_csv(url_csv, encoding='utf-8-sig')
        df.columns = [re.sub(r'[^A-Z0-9]', '', str(c).upper()) for c in df.columns]
        return df.dropna(how='all')
    except: return pd.DataFrame()

# ==============================================================================
# 3. SISTEMA DE LOGIN (FIX VARIABLE CLAVE)
# ==============================================================================
if "authenticated" not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_log1, c_log2, c_log3 = st.columns([1, 2, 1])
    with c_log2:
        if os.path.exists("CMSG.png"): st.image("CMSG.png", width=220)
        st.title("Plataforma Control Laboral")
        p_login = st.text_input("Contraseña Corporativa:", type="password").strip()
        if st.button("ACCEDER AL PORTAL", use_container_width=True):
            df_usuarios = cargar_datos(ID_USUARIOS, "Usuarios")
            if not df_usuarios.empty:
                col_c_final = next((c for c in df_usuarios.columns if 'CLAVE' in str(c).upper()), 'CLAVE')
                match = df_usuarios[df_usuarios[col_c_final].astype(str).str.strip() == p_login]
                if not match.empty:
                    u_inf = match.iloc[0]
                    st.session_state.update({
                        "authenticated": True, 
                        "u_nom": u_inf.get('NOMBRE',''), 
                        "u_rol": u_inf.get('ROL',''), 
                        "u_emp": u_inf.get('EMPRESA',''), 
                        "u_email": u_inf.get('EMAIL','')
                    })
                    st.rerun()
                else: st.error("Contraseña incorrecta.")
    st.stop()

# ==============================================================================
# 4. SIDEBAR Y PERMISOS DE PESTAÑAS (FILTRADO SEGÚN SERGIO)
# ==============================================================================
with st.sidebar:
    if os.path.exists("CMSG.png"): st.image("CMSG.png", use_container_width=True)
    st.markdown(f"👤 **{st.session_state['u_nom']}**")
    st.markdown(f"🏢 **{st.session_state['u_emp']}**")
    st.markdown("---")
    a_gest = st.selectbox("Año de Gestión", ["2026", "2025"])
    df_av_maestro = cargar_datos(ID_AVANCE, a_gest)
    cols_m_ready = [c for c in df_av_maestro.columns if c in MESES_LISTA] if not df_av_maestro.empty else []
    m_sidebar_sel = st.selectbox("Mes de Análisis", ["AÑO COMPLETO"] + cols_m_ready)
    if st.button("🚪 CERRAR SESIÓN"):
        for k_s in list(st.session_state.keys()): del st.session_state[k_s]
        st.rerun()

rol_s = st.session_state["u_rol"]
if rol_s == "USUARIO":
    t_list_s = ["📉 Dashboard", "📤 Carga Mensual", "👥 DOTACION"]
else:
    t_list_s = ["📉 Dashboard", "📊 KPIS EMPRESAS", "📤 Carga Mensual", "👥 DOTACION", "⚙️ Admin"]

tabs_s = st.tabs(t_list_s)

# ==============================================================================
# 5. PESTAÑA 1: DASHBOARD (INDICADORES + GRÁFICOS RESTAURADOS)
# ==============================================================================
with tabs_s[t_list_s.index("📉 Dashboard")]:
    df_id_empresas_all = cargar_datos(ID_EMPRESAS, "HOJA1")
    if not df_av_maestro.empty:
        col_e_m = next((c for c in df_av_maestro.columns if 'EMP' in str(c).upper()), 'EMPRESA')
        # Filtro de seguridad
        df_f_s = df_av_maestro[df_av_maestro[col_e_m] == st.session_state["u_emp"]] if rol_s == "USUARIO" else df_av_maestro
        c_f_s = [m_sidebar_sel] if m_sidebar_sel != "AÑO COMPLETO" else cols_m_ready
        
        # --- LÓGICA DE CUMPLIMIENTO (ESTADO 9 EXCLUIDO) ---
        df_num_s = df_f_s[c_f_s].apply(pd.to_numeric, errors='coerce')
        df_audit_s = df_num_s.copy()
        df_audit_s[df_audit_s == 9] = pd.NA # AQUÍ SE EXCLUYE EL ESTADO 9
        
        total_evaluados = df_audit_s.count().sum()
        total_aprobados = (df_audit_s == 5).sum().sum()
        # El promedio solo considera los puntos con información válida (1-8)
        perc_s = (total_aprobados / total_evaluados * 100) if total_evaluados > 0 else 0
        
        st.header(f"Seguimiento de Cumplimiento - {m_sidebar_sel} {a_gest}")
        km1, km2, km3 = st.columns(3)
        km1.metric("EECC Evaluadas", len(df_f_s))
        km2.metric("% Cumplimiento Promedio", f"{perc_s:.1f}%")
        km3.metric("Revisiones con éxito", int(total_aprobados))

        # --- GRÁFICO DE BARRAS EVOLUTIVO (OCULTA ESTADO 9) ---
        if m_sidebar_sel == "AÑO COMPLETO":
            st.divider(); st.write("### 📈 Evolución Mensual de Estados (Excluyendo N/C)")
            res_evo_s = []
            for m_loop in cols_m_ready:
                counts_loop = df_f_s[m_loop].value_counts()
                for c_loop, cant_loop in counts_loop.items():
                    if pd.notna(c_loop) and int(c_loop) != 9: # EXCLUIMOS EL 9 DEL GRÁFICO
                        res_evo_s.append({'Mes': m_loop, 'Estado': MAPA_ESTADOS.get(int(c_loop), "S/I"), 'Cantidad': cant_loop})
            if res_evo_s:
                st.plotly_chart(px.bar(pd.DataFrame(res_evo_s), x='Mes', y='Cantidad', color='Estado', color_discrete_map=COLORES_ESTADOS, barmode='stack'), use_container_width=True)

        st.divider(); emp_sel_s = st.selectbox("Analizar Empresa Detallada:", sorted(df_f_s[col_e_m].unique()))
        df_es_s = df_f_s[df_f_s[col_e_m] == emp_sel_s]
        c_iz_s, c_de_s = st.columns([3, 1.2])
        
        with c_iz_s:
            # Gráfico de Pie (Excluye el 9)
            p_pie_s = df_es_s[cols_m_ready].stack().value_counts().reset_index(); p_pie_s.columns = ['Cod', 'Cant']
            p_pie_s = p_pie_s[p_pie_s['Cod'] != 9] # FILTRO ESTADO 9
            p_pie_s['Estado'] = p_pie_s['Cod'].map(MAPA_ESTADOS)
            st.plotly_chart(px.pie(p_pie_s, values='Cant', names='Estado', hole=.4, color='Estado', color_discrete_map=COLORES_ESTADOS, title=f"Distribución Actual: {emp_sel_s}"), use_container_width=True)
            
            # Grilla de 12 Meses
            st.write("#### 📜 Semáforo Histórico de Gestión")
            h1_s, h2_s = cols_m_ready[:6], cols_m_ready[6:]
            def render_grid_s(lista_m):
                cs_s = st.columns(6)
                for i_s, m_s in enumerate(lista_m):
                    v_s = int(df_es_s[m_s].values[0]) if pd.notna(df_es_s[m_s].values[0]) else 8
                    t_s = MAPA_ESTADOS.get(v_s, "S/I"); b_s = COLORES_ESTADOS.get(t_s, "#555555"); tc_s = "#000000" if t_s in ["Observado", "Cumple", "En Revision"] else "#FFFFFF"
                    cs_s[i_s].markdown(f"<div style='text-align:center; border:1px solid #ddd; padding:8px; border-radius:8px; background-color:{b_s}; color:{tc_s}; min-height:65px; display:flex; flex-direction:column; justify-content:center;'><b style='font-size:11px;'>{m_s}</b><br><span style='font-size:8px; font-weight:bold;'>{t_s.upper()}</span></div>", unsafe_allow_html=True)
            render_grid_s(h1_s); st.write(""); render_grid_s(h2_s)

        with c_de_s:
            st.subheader("📄 Certificado")
            m_p_cert = st.selectbox("Periodo Certificado:", cols_m_ready, key="s_p_cert_s")
            if st.button("Consultar en Drive", use_container_width=True):
                mt_cert = df_id_empresas_all[df_id_empresas_all['EMPRESA'].str.contains(emp_sel_s[:10], case=False, na=False)]
                if not mt_cert.empty:
                    id_fc_s = str(mt_cert.iloc[0]['IDCARPETA']).strip()
                    n_fc_s = f"Certificado.{MAPA_MESES_NUM[m_p_cert]}{a_gest}.pdf"
                    r_fc_s = requests.get(URL_APPS_SCRIPT, params={"nombre": n_fc_s, "carpeta": id_fc_s})
                    if r_fc_s.text.startswith("http"): st.session_state["link_s"] = r_fc_s.text.strip()
            if "link_s" in st.session_state: st.link_button("📥 DESCARGAR PDF", st.session_state["link_s"], use_container_width=True)

# ==============================================================================
# 6. PESTAÑA 2: KPIS (ADMIN)
# ==============================================================================
if rol_s != "USUARIO":
    with tabs_s[t_list_s.index("📊 KPIS EMPRESAS")]:
        st.header("📊 Detalle de Dotación Mensual")
        m_k_sel = st.selectbox("Seleccione Mes:", MESES_LISTA, key="m_k_final_s")
        dk_s = cargar_datos(ID_COLABORADORES, f"{m_k_sel.capitalize()}{a_gest[-2:]}")
        if not dk_s.empty: st.dataframe(dk_s, use_container_width=True)

# ==============================================================================
# 7. PESTAÑA 3: CARGA MENSUAL (EXPLÍCITA - 8 CARGADORES)
# ==============================================================================
with tabs_s[t_list_s.index("📤 Carga Mensual")]:
    st.header("📤 Portal de Carga de Información")
    if m_sidebar_sel == "AÑO COMPLETO": st.warning("Seleccione un Mes en el sidebar para cargar.")
    else:
        cm1_s, cm2_s = st.columns([1.7, 1.3])
        with cm2_s:
            st.markdown("""<div class='caja-instrucciones' style='border-left: 8px solid #FF8C00;'>
            <h4>📖 Guía de Carga</h4><p style='font-size:14px; color:#d9534f;'><b>⚠️ REGLA: MÁXIMO 20MB POR ARCHIVO.</b></p>
            <ul style='font-size:13px; line-height:1.7;'>
                <li><b>1. Liquidaciones:</b> PDF con todas las del mes.</li>
                <li><b>2. Pagos:</b> PDF con comprobantes de pago.</li>
                <li><b>3. Cotizaciones:</b> Planillas Previred.</li>
                <li><b>4. Libro:</b> Archivo CSV (LRE).</li>
                <li><b>5. Comp. DT:</b> Comprobante de registro en DT.</li>
                <li><b>6. F30:</b> Certificado actualizado.</li>
                <li><b>7. F30-1:</b> Certificado actualizado.</li>
                <li><b>8. Planilla Control:</b> Archivo Excel (.XLS).</li>
            </ul></div>""", unsafe_allow_html=True)
        with cm1_s:
            e_u_m_s = st.session_state['u_emp'] if rol_s == "USUARIO" else st.selectbox("Empresa Evaluada:", sorted(df_av_maestro[col_e_m].unique()), key="sel_m_s")
            st.divider()
            
            def master_upload(f, p, emp):
                if f and f.size <= 20*1024*1024:
                    mt = df_id_empresas_all[df_id_empresas_all['EMPRESA'].str.contains(emp[:10], case=False, na=False)]
                    if not mt.empty:
                        idf = str(mt.iloc[0]['IDCARPETA']).strip(); ex = f.name.split('.')[-1]
                        py = {"tipo":"mensual","id_carpeta":idf,"anio":a_gest,"nombre_final":f"{p}_{m_sidebar_sel}.{ex}","mes_nombre":MAPA_MESES_CARP[m_sidebar_sel],"archivo_base64":base64.b64encode(f.read()).decode('utf-8')}
                        if requests.post(URL_APPS_SCRIPT, data=py).status_code == 200: st.success(f"Cargado: {p}")
                elif f: st.error("⚠️ Excede 20MB.")

            # CARGADORES UNO A UNO (PARA MÁXIMA EXTENSIÓN Y ORDEN)
            u1 = st.file_uploader("1. Liquidaciones de Sueldo", type=["pdf"], key="u1"); b1 = st.button("Enviar Liquidaciones", key="bu1")
            if b1: master_upload(u1, "LIQ", e_u_m_s)
            
            u2 = st.file_uploader("2. Comprobantes de Pago", type=["pdf"], key="u2"); b2 = st.button("Enviar Pagos", key="bu2")
            if b2: master_upload(u2, "PAGOS", e_u_m_s)
            
            u3 = st.file_uploader("3. Cotizaciones Previred", type=["pdf"], key="u3"); b3 = st.button("Enviar Cotizaciones", key="bu3")
            if b3: master_upload(u3, "PREVIRED", e_u_m_s)
            
            u4 = st.file_uploader("4. Libro de Remuneraciones (CSV)", type=["csv"], key="u4"); b4 = st.button("Enviar Libro", key="bu4")
            if b4: master_upload(u4, "LIBRO", e_u_m_s)
            
            u5 = st.file_uploader("5. Comprobante Envío LRE a DT", type=["pdf"], key="u5"); b5 = st.button("Enviar Comp. DT", key="bu5")
            if b5: master_upload(u5, "DT", e_u_m_s)
            
            u6 = st.file_uploader("6. Certificado F30", type=["pdf"], key="u6"); b6 = st.button("Enviar F30", key="bu6")
            if b6: master_upload(u6, "F30", e_u_m_s)
            
            u7 = st.file_uploader("7. Certificado F30-1", type=["pdf"], key="u7"); b7 = st.button("Enviar F30-1", key="bu7")
            if b7: master_upload(u7, "F301", e_u_m_s)
            
            u8 = st.file_uploader("8. Planilla de Control Mensual", type=["xlsx","xls"], key="u8"); b8 = st.button("Enviar Planilla", key="bu8")
            if b8: master_upload(u8, "CTRL", e_u_m_s)

            st.divider()
            if st.button("🏁 FINALIZAR CARGA Y NOTIFICAR", key="btn_not_m_s", use_container_width=True):
                requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email","empresa":e_u_m_s,"usuario":st.session_state["u_nom"],"periodo":f"MENSUAL: {m_sidebar_sel} {a_gest}"})
                st.success("Notificación enviada.")

# ==============================================================================
# 8. PESTAÑA 4: DOTACION (DINÁMICA ALTA/BAJA - EXPLÍCITA)
# ==============================================================================
with tabs_s[t_list_s.index("👥 DOTACION")]:
    st.header("👥 Gestión de Movimientos de Personal")
    # RADIO QUE CAMBIA LOS REQUISITOS EN TIEMPO REAL
    t_mov_s = st.radio("Acción a Informar:", ["🟢 Alta (Nuevo Ingreso)", "🔴 Baja (Egreso/Traslado)"], horizontal=True)
    st.divider()
    
    col_dx1, col_dx2 = st.columns([1.7, 1.3])
    with col_dx2:
        if "Alta" in t_mov_s:
            color_dx = "#1E90FF"; tit_dx = "Requisitos de Alta"
            req_dx = """<li>Contrato de Trabajo</li><li>Anexo de Traslado</li><li>Cédula Identidad</li>
                        <li>Certificado Afiliacion AFP</li><li>Certificado Afiliacion Salud</li>
                        <li>Registro Contrato en DT</li><li>Entrega de RIOHS</li>"""
        else:
            color_dx = "#d9534f"; tit_dx = "Requisitos de Baja"
            req_dx = """<li>Finiquito Legalizado + Comprobante Pago</li><li>Anexo Traslado de Faena</li>"""
            
        st.markdown(f"""<div class='caja-instrucciones' style='border-left: 8px solid {color_dx};'>
        <h4>📌 {tit_dx}</h4><p style='font-size:14px; color:#d9534f;'><b>REGLA: MÁXIMO 20MB POR ARCHIVO.</b></p>
        <ul style='font-size:14px; line-height:1.7;'>{req_dx}</ul></div>""", unsafe_allow_html=True)
    
    with col_dx1:
        e_c_dx = st.session_state['u_emp'] if rol_s == "USUARIO" else st.selectbox("Empresa Contratista:", sorted(df_av_maestro[col_e_m].unique()), key="sel_d_s")
        ci1_s, ci2_s = st.columns(2)
        with ci1_s: t_nom_s = st.text_input("Nombre Trabajador:", placeholder="Nombre Apellido")
        with ci2_s: 
            t_rut_s = st.text_input("RUT (ej: 12345678-9):", placeholder="12345678-9")
            r_ok_s = validar_rut(t_rut_s) if t_rut_s else False
            if t_rut_s: st.caption("✅ RUT Válido" if r_ok_s else "❌ RUT Inválido")
        
        ci3_s, ci4_s = st.columns(2)
        with ci3_s: t_fec_s = st.date_input("Fecha Efectiva:", datetime.now())
        with ci4_s:
            if "Baja" in t_mov_s: t_cau_s = st.selectbox("Causal Legal:", CAUSALES_FINIQUITO)
            else: t_cau_s = "Nuevo Ingreso"

        st.divider()
        ar_dot_s = st.file_uploader("Arrastre los documentos (PDF):", type=["pdf"], accept_multiple_files=True, key="bulk_dot_s")
        
        # BOTÓN DE CARGA DE RRHH (RESTAURADO)
        if st.button("🚀 PROCESAR MOVIMIENTO Y NOTIFICAR", key="btn_not_d_s", use_container_width=True):
            if t_nom_s and r_ok_s and ar_dot_s:
                if any(az.size > 20*1024*1024 for az in ar_dot_s): st.error("⚠️ Uno o más archivos exceden los 20MB.")
                else:
                    mt_dx = df_id_empresas_all[df_id_empresas_all['EMPRESA'].str.contains(e_c_dx[:10], case=False, na=False)]
                    if not mt_dx.empty:
                        idf_dx = str(mt_dx.iloc[0]['IDCARPETA']).strip()
                        for fi_s in ar_dot_s:
                            requests.post(URL_APPS_SCRIPT, data={"tipo":"colaborador","id_carpeta":idf_dx,"nombre_persona":t_nom_s.upper(),"rut":t_rut_s,"nombre_final":fi_s.name,"archivo_base64":base64.b64encode(fi_s.read()).decode('utf-8')})
                        
                        # Email dinámico para tu Script (Sin 'Periodo' estorbando)
                        body_rrhh = f"Acción: {t_mov_s}\nTrabajador: {t_nom_s.upper()}\nFecha: {t_fec_s.strftime('%d/%m/%Y')}\nCausal: {t_cau_s}"
                        requests.post(URL_APPS_SCRIPT, data={"accion":"enviar_email", "empresa":e_c_dx, "usuario":st.session_state["u_nom"], "periodo": body_rrhh})
                        st.success(f"✅ Se ha procesado el movimiento de {t_nom_s.upper()}.")
            else: st.warning("Complete todos los campos y cargue la documentación.")

# ==============================================================================
# 9. PESTAÑA 5: ADMIN
# ==============================================================================
if rol_s != "USUARIO":
    with tabs_s[t_list_s.index("⚙️ Admin")]:
        st.header("⚙️ Gestión Administrativa"); st.dataframe(cargar_datos(ID_USUARIOS, "Usuarios"), use_container_width=True)

st.markdown("---")
st.caption("Control Laboral CMSG | Gestión de Contratistas | Desarrollado por C & S Asociados Ltda.")