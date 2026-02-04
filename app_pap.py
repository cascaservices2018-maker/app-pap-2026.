import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import io
import time
import altair as alt
import unicodedata

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Gestión PAP - Nube",
    layout="wide",
    page_icon="☁️",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🎨 PERSONALIZACIÓN DE COLORES (CSS)
# ==========================================
COLOR_FONDO_PRINCIPAL = "#A60000"
COLOR_BARRA_LATERAL = "#262730"

estilos_css = f"""
<style>
    .stApp {{ background-color: {COLOR_FONDO_PRINCIPAL}; }}
    [data-testid="stSidebar"] {{ background-color: {COLOR_BARRA_LATERAL}; }}
    [data-testid="stMetricValue"], h1, h2, h3, p, li {{ color: white !important; }}
    .vega-embed svg text {{ fill: white !important; }}
    .streamlit-expanderHeader {{ background-color: #262730; color: white; }}
</style>
"""
st.markdown(estilos_css, unsafe_allow_html=True)

# ==========================================
# 📖 DICCIONARIO INTELIGENTE
# ==========================================
DICCIONARIO_CORRECTO = {
    # INFRAESTRUCTURA
    "diseno arquitectonico": "Diseño arquitectónico",
    "diseño arquitectonico": "Diseño arquitectónico",
    "arquitectonico": "Diseño arquitectónico",
    "arquitectura": "Diseño arquitectónico",
    "planos": "Diseño arquitectónico",
    "mantenimiento": "Mantenimiento",
    "teatrales": "Productos teatrales",
    "productos": "Productos teatrales",
    "producto": "Productos teatrales",
    # GESTIÓN
    "administracion": "Administración", "admin": "Administración",
    "financiamiento": "Financiamiento", "finanza": "Financiamiento",
    "vinculacion": "Vinculación", "vinc": "Vinculación",
    "gestion": "Gestión", "gestión": "Gestión",
    # COMUNICACIÓN
    "comunicacion": "Comunicación", "comunica": "Comunicación",
    "diseno": "Diseño", "diseño": "Diseño",
    "grafico": "Diseño",
    "difusion": "Difusión", "difucion": "Difusión",
    "memoria": "Memoria/Archivo", "archivo": "Memoria/Archivo",
    # INVESTIGACIÓN
    "investigacion": "Investigación", "investigasion": "Investigación"
}

def normalizar_comparacion(texto):
    if pd.isna(texto): return ""
    texto = str(texto).lower().strip()
    if texto in ["nan", "none", ""]: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')

def limpiar_textos(texto_sucio):
    if pd.isna(texto_sucio): return ""
    texto_str = str(texto_sucio).strip()
    if texto_str in ["", "nan", "None", "NaN"]: return ""
    palabras = [p.strip() for p in texto_str.split(',')]
    palabras_corregidas = []
    for p in palabras:
        p_norm = normalizar_comparacion(p)
        encontrado = False
        for error_clave, correccion_perfecta in DICCIONARIO_CORRECTO.items():
            if error_clave in p_norm:
                palabras_corregidas.append(correccion_perfecta)
                encontrado = True
                break
        if not encontrado:
            palabras_corregidas.append(p.strip())
    return ", ".join(sorted(list(dict.fromkeys(palabras_corregidas))))

# ==========================================
# 🔗 CONFIGURACIÓN SISTEMA
# ==========================================
LOGO_URL = "https://github.com/cascaservices2018-maker/app-pap-2026./blob/main/cedramh3-removebg-preview.png?raw=true"
CATEGORIAS_LISTA = ["Gestión", "Comunicación", "Infraestructura", "Investigación"]
SUBCATEGORIAS_SUGERIDAS = [
    "Administración", "Financiamiento", "Vinculación",
    "Memoria/archivo CEDRAM", "Memoria/archivo PAP", "Diseño", "Difusión",
    "Diseño arquitectónico", "Mantenimiento", "Productos teatrales"
]

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=5)
        if not df.empty:
            df.columns = df.columns.str.strip()
            if "Periodo" in df.columns:
                df["Periodo"] = df["Periodo"].astype(str).str.strip().str.title()
        return df
    except: return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
    except Exception as e: st.error(f"Error al guardar: {e}")

def graficar_oscuro(df, x_col, y_col, titulo_x, titulo_y, color_barra="#FFFFFF"):
    chart = alt.Chart(df).mark_bar(color=color_barra).encode(
        x=alt.X(x_col, title=titulo_x, sort='-y'),
        y=alt.Y(y_col, title=titulo_y),
        tooltip=[x_col, y_col]
    ).configure_axis(labelColor='white', titleColor='white', gridColor='#660000').properties(height=300)
    st.altair_chart(chart, theme="streamlit", width="stretch")

# --- VARIABLES DE ESTADO ---
if "form_seed" not in st.session_state: st.session_state.form_seed = 0
if "proy_recien_creado" not in st.session_state: st.session_state.proy_recien_creado = None
if "df_buffer_masivo" not in st.session_state: st.session_state.df_buffer_masivo = None
if "last_selected_project" not in st.session_state: st.session_state.last_selected_project = None
if "stats_download" not in st.session_state: st.session_state.stats_download = {}

# --- SIDEBAR ---
with st.sidebar:
    st.image(LOGO_URL, width=280)
    st.markdown("### ⚙️ Panel de Control")
    st.info("Sistema de Gestión de Proyectos PAP - 2026")
    st.markdown("---")
    st.write("Bienvenido al sistema colaborativo.")

col_logo, col_titulo = st.columns([2, 8])
with col_logo: st.image(LOGO_URL, width=170)
with col_titulo: st.title("Base de datos PAP PERIODOS 2019-2026")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["1. Registrar", "2. Carga Masiva", "3. 📝 Buscar/Editar", "4. 📊 Gráficas", "5. 📥 Descargas", "6. Glosario"])

# ==========================================
# PESTAÑA 1: REGISTRO
# ==========================================
with tab1:
    st.subheader("Nuevo Proyecto")
    with st.form("form_proyecto", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        semilla = st.session_state.form_seed
        anio = c1.number_input("Año", 2019, 2030, datetime.now().year, key=f"anio_{semilla}")
        periodo = c2.selectbox("Periodo", ["Primavera", "Verano", "Otoño"], key=f"periodo_{semilla}")
        cats = c3.multiselect("Categoría(s)", CATEGORIAS_LISTA, key=f"cats_{semilla}")
        nombre = st.text_input("Nombre del Proyecto", key=f"nombre_{semilla}")
        desc = st.text_area("Descripción", key=f"desc_{semilla}")
        ce, cc = st.columns(2)
        num_ent = ce.number_input("Estimado Entregables", 1, step=1, key=f"num_{semilla}")
        comen = cc.text_area("Comentarios", key=f"comen_{semilla}")

        if st.form_submit_button("💾 Guardar Proyecto"):
            if not nombre: st.error("⚠️ El nombre es obligatorio.")
            elif not cats: st.error("⚠️ Elige categoría.")
            else:
                df = load_data("Proyectos")
                if not df.empty and "Nombre del Proyecto" in df.columns and nombre in df["Nombre del Proyecto"].values:
                    st.warning("⚠️ Ya existe.")
                else:
                    nuevo = {"Año": anio, "Periodo": periodo, "Nombre del Proyecto": nombre, "Descripción": desc, "Num_Entregables": num_ent, "Categoría": limpiar_textos(", ".join(cats)), "Comentarios": comen, "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    save_data(pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True), "Proyectos")
                    st.success("¡Guardado!")
                    
                    # --- AUTO-SELECCIÓN PARA PESTAÑA 2 ---
                    st.session_state.proy_recien_creado = nombre
                    st.session_state["selector_proyectos_masivo"] = nombre # <--- ESTO FUERZA EL CAMBIO
                    
                    st.session_state.form_seed += 1
                    time.sleep(1); st.rerun()

# ==========================================
# PESTAÑA 2: CARGA MASIVA (BÚNKER DE DATOS)
# ==========================================
with tab2:
    st.subheader("⚡ Carga Rápida y Edición")
    st.info("💡 **Modo Búnker:** La tabla NO se actualizará ni borrará nada hasta que presiones 'Guardar Cambios'. Copia y pega con confianza.")

    df_p = load_data("Proyectos")
    if df_p.empty: st.warning("Cargando...")
    elif "Nombre del Proyecto" in df_p.columns:

        lista_proy = sorted(df_p["Nombre del Proyecto"].unique().tolist())
        
        # El índice por defecto ya no es tan crítico porque forzamos el session_state arriba, 
        # pero lo dejamos por si acaso.
        idx_defecto = 0
        if st.session_state.proy_recien_creado in lista_proy:
            idx_defecto = lista_proy.index(st.session_state.proy_recien_creado)

        proy_sel = st.selectbox("Selecciona Proyecto:", lista_proy, index=idx_defecto, key="selector_proyectos_masivo")

        info = df_p[df_p["Nombre del Proyecto"] == proy_sel].iloc[0]
        cat, estim = info.get("Categoría", "General"), int(info.get("Num_Entregables", 5))
        st.caption(f"Categoría: {cat} | Espacios: {estim}")

        # --- GESTIÓN DE CARGA (SOLO AL CAMBIAR PROYECTO) ---
        if st.session_state.last_selected_project != proy_sel:
            df_e = load_data("Entregables")
            exist = pd.DataFrame()
            if not df_e.empty:
                exist = df_e[df_e["Proyecto_Padre"] == proy_sel]

            if not exist.empty:
                temp_df = exist[["Entregable", "Contenido", "Subcategoría", "Plantillas"]].rename(
                    columns={"Entregable": "Nombre_Entregable", "Subcategoría": "Subcategorías", "Plantillas": "Plantillas_Usadas"}
                )
            else:
                temp_df = pd.DataFrame("", index=range(estim), columns=["Nombre_Entregable", "Contenido", "Subcategorías", "Plantillas_Usadas"])

            # Inicializamos el buffer limpio
            st.session_state.df_buffer_masivo = temp_df.fillna("").astype(str)
            st.session_state.last_selected_project = proy_sel

        # --- FORMULARIO DE AISLAMIENTO (st.form) ---
        with st.form(key=f"form_masivo_{proy_sel}"):
            edited_df = st.data_editor(
                st.session_state.df_buffer_masivo,
                num_rows="dynamic",
                width="stretch",
                column_config={
                    "Subcategorías": st.column_config.TextColumn("Subcategoría(s)", help=f"Sugerencias: {', '.join(SUBCATEGORIAS_SUGERIDAS)}"),
                    "Nombre_Entregable": st.column_config.TextColumn("Nombre", required=True),
                    "Contenido": st.column_config.TextColumn("Contenido", width="large"),
                    "Plantillas_Usadas": st.column_config.TextColumn("Link/Plantilla")
                }
            )

            submit_btn = st.form_submit_button("🚀 Guardar Cambios (Definitivo)")

        # --- LÓGICA DE GUARDADO (FUERA DEL FORM, SE ACTIVA AL ENVIAR) ---
        if submit_btn:
            # 1. Sanitización Final
            df_final_process = edited_df.astype(str).replace({"nan": "", "None": "", "NaN": ""})

            # 2. Filtrar vacíos
            validos = df_final_process[
                (df_final_process["Nombre_Entregable"].str.strip() != "")
            ].copy()

            if validos.empty: st.error("La tabla está vacía o no tiene nombres.")
            else:
                try:
                    # 3. Aplicar diccionario y preparar datos
                    validos["Subcategorías"] = validos["Subcategorías"].apply(limpiar_textos)
                    df_m = load_data("Entregables")

                    # Eliminar registros previos de este proyecto
                    if not df_m.empty: df_m = df_m[df_m["Proyecto_Padre"] != proy_sel]

                    nuevos = []
                    hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for _, r in validos.iterrows():
                        nuevos.append({
                            "Proyecto_Padre": proy_sel,
                            "Entregable": r["Nombre_Entregable"],
                            "Contenido": r["Contenido"],
                            "Categoría": cat,
                            "Subcategoría": r["Subcategorías"],
                            "Plantillas": r["Plantillas_Usadas"],
                            "Fecha_Registro": hoy
                        })

                    # 4. Guardar en Google Sheets
                    save_data(pd.concat([df_m, pd.DataFrame(nuevos)], ignore_index=True), "Entregables")

                    # 5. Actualizar la memoria local
                    st.session_state.df_buffer_masivo = df_final_process

                    st.success("¡Guardado exitoso!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# ==========================================
# PESTAÑA 3: BÚSQUEDA Y EDICIÓN
# ==========================================
with tab3:
    st.header("📝 Edición de Base de Datos")
    df_proy = load_data("Proyectos"); df_ent = load_data("Entregables")

    if not df_proy.empty and "Año" in df_proy.columns:
        if "Categoría" in df_proy.columns: df_proy["Categoría"] = df_proy["Categoría"].apply(limpiar_textos)
        if not df_ent.empty: df_ent["Subcategoría"] = df_ent["Subcategoría"].apply(limpiar_textos)

        cats_f = set(); subs_f = set()
        for c in df_proy["Categoría"].dropna(): cats_f.update([limpiar_textos(x) for x in str(c).split(',')])
        if not df_ent.empty:
            for s in df_ent["Subcategoría"].dropna(): subs_f.update([limpiar_textos(x) for x in str(s).split(',')])

        c0, c1, c2, c3, c4 = st.columns(5)
        f_nom = c0.multiselect("🔍 Proyecto:", sorted(df_proy["Nombre del Proyecto"].unique()), key="f_p3_nom")
        f_ano = c1.multiselect("Año:", sorted(df_proy["Año"].unique()), key="f_p3_ano")
        f_per = c2.multiselect("Periodo:", ["Primavera", "Verano", "Otoño"], key="f_p3_per")
        f_cat = c3.multiselect("Categoría:", sorted(list(cats_f)), key="f_p3_cat")
        f_sub = c4.multiselect("Subcategoría:", sorted(list(subs_f)), key="f_p3_sub")

        df_v = df_proy.copy(); df_ev = df_ent.copy() if not df_ent.empty else pd.DataFrame()

        if f_nom: df_v = df_v[df_v["Nombre del Proyecto"].isin(f_nom)]
        if f_ano: df_v = df_v[df_v["Año"].isin(f_ano)]
        if f_per: df_v = df_v[df_v["Periodo"].astype(str).str.strip().isin(f_per)]
        if f_cat: df_v = df_v[df_v["Categoría"].apply(lambda x: any(limpiar_textos(c) in f_cat for c in str(x).split(',')))]
        if f_sub and not df_ev.empty:
            df_ev = df_ev[df_ev["Subcategoría"].apply(lambda x: any(limpiar_textos(s) in f_sub for s in str(x).split(',')))]
            df_v = df_v[df_v["Nombre del Proyecto"].isin(df_ev["Proyecto_Padre"].unique())]

        st.markdown("---")
        with st.expander(f"📂 1. Tabla de Proyectos ({len(df_v)})", expanded=True):
            ed_p = st.data_editor(df_v, width="stretch", key="ep", num_rows="fixed", column_config={
                "Categoría": st.column_config.TextColumn("Categoría(s)"),
                "Año": st.column_config.NumberColumn("Año", format="%d", step=1, required=True),
                "Periodo": st.column_config.SelectboxColumn("Periodo", options=["Primavera", "Verano", "Otoño"], required=True)
            })
            if st.button("💾 Actualizar Proyectos"):
                if "Categoría" in ed_p.columns: ed_p["Categoría"] = ed_p["Categoría"].apply(limpiar_textos)
                df_master_proy = load_data("Proyectos"); df_master_proy.update(ed_p); save_data(df_master_proy, "Proyectos")
                st.success("✅ Actualizado.")

        with st.expander("📦 2. Entregables Asociados", expanded=True):
            if not df_ent.empty:
                df_ef = df_ev[df_ev["Proyecto_Padre"].isin(df_v["Nombre del Proyecto"].unique())] if f_sub else df_ent[df_ent["Proyecto_Padre"].isin(df_v["Nombre del Proyecto"].unique())]
                if not df_ef.empty:
                    ed_e = st.data_editor(df_ef, width="stretch", key="ee", num_rows="fixed", column_config={"Subcategoría": st.column_config.TextColumn("Subcategoría")})
                    if st.button("💾 Actualizar Entregables"):
                        if "Subcategoría" in ed_e.columns: ed_e["Subcategoría"] = ed_e["Subcategoría"].apply(limpiar_textos)
                        df_master_ent = load_data("Entregables"); df_master_ent.update(ed_e); save_data(df_master_ent, "Entregables")
                        st.success("✅ Actualizado.")
                else: st.info("Sin entregables.")
            else: st.info("Vacío.")

        with st.expander("🗑️ Zona de Borrado", expanded=False):
            ops = df_v["Nombre del Proyecto"].unique()
            if len(ops) > 0:
                d = st.selectbox("Eliminar:", ops)
                if st.button("Eliminar Definitivamente"):
                    save_data(df_proy[df_proy["Nombre del Proyecto"]!=d], "Proyectos")
                    if not df_ent.empty: save_data(df_ent[df_ent["Proyecto_Padre"]!=d], "Entregables")
                    st.success("Eliminado"); time.sleep(1); st.rerun()
    else: st.info("Cargando...")

# ==========================================
# PESTAÑA 4: GRÁFICAS
# ==========================================
with tab4:
    st.header("📊 Estadísticas en Vivo")
    st.info("ℹ️ **Tip:** Usa los tres puntitos sobre la gráfica para descargar imagen.")

    try: df_p_s = load_data("Proyectos"); df_e_s = load_data("Entregables")
    except: df_p_s = pd.DataFrame(); df_e_s = pd.DataFrame()

    if not df_p_s.empty and "Año" in df_p_s.columns:
        if "Categoría" in df_p_s.columns: df_p_s["Categoría"] = df_p_s["Categoría"].apply(limpiar_textos)
        if not df_e_s.empty: df_e_s["Subcategoría"] = df_e_s["Subcategoría"].apply(limpiar_textos)

        cats_g = set(); subs_g = set()
        for c in df_p_s["Categoría"].dropna(): cats_g.update([x.strip() for x in str(c).split(',') if x.strip()])
        if not df_e_s.empty:
            for s in df_e_s["Subcategoría"].dropna(): subs_g.update([x.strip() for x in str(s).split(',') if x.strip()])

        c1, c2, c3, c4 = st.columns(4)
        yg = c1.multiselect("Año", sorted(df_p_s["Año"].unique()), default=sorted(df_p_s["Año"].unique()), key="g_year")
        pg = c2.multiselect("Periodo", ["Primavera", "Verano", "Otoño"], key="g_per")
        cg = c3.multiselect("Categoría", sorted(list(cats_g)), key="g_cat")
        sg = c4.multiselect("Subcategoría", sorted(list(subs_g)), key="g_sub")

        df_f = df_p_s.copy()
        if yg: df_f = df_f[df_f["Año"].isin(yg)]
        if pg: df_f = df_f[df_f["Periodo"].astype(str).str.strip().isin(pg)]
        if cg: df_f = df_f[df_f["Categoría"].apply(lambda x: any(item in cg for item in str(x).split(', ')))]

        df_e_f = df_e_s.copy() if not df_e_s.empty else pd.DataFrame()
        if sg and not df_e_f.empty:
            df_e_f = df_e_f[df_e_f["Subcategoría"].apply(lambda x: any(item in sg for item in str(x).split(', ')))]
            df_f = df_f[df_f["Nombre del Proyecto"].isin(df_e_f["Proyecto_Padre"].unique())]

        if df_f.empty: st.warning("Sin datos.")
        else:
            st.markdown("---")
            if df_f["Año"].nunique() > 0:
                st.subheader("📅 Evolución Anual / Resumen")
                pa = df_f["Año"].value_counts().reset_index(); pa.columns=["Año","Total"]; pa["Tipo"]="Proyectos"
                vis = df_f["Nombre del Proyecto"].unique()
                if not df_e_s.empty:
                    ev = df_e_f[df_e_f["Proyecto_Padre"].isin(vis)] if sg else df_e_s[df_e_s["Proyecto_Padre"].isin(vis)]
                    mapa = df_f.set_index("Nombre del Proyecto")["Año"].to_dict()
                    ev["Año_R"] = ev["Proyecto_Padre"].map(mapa); ev = ev.dropna(subset=["Año_R"])
                    ea = ev["Año_R"].value_counts().reset_index(); ea.columns=["Año","Total"]; ea["Tipo"]="Entregables"
                else: ea = pd.DataFrame()

                df_chart = pd.concat([pa, ea])
                if not df_chart.empty:
                    base = alt.Chart(df_chart).encode(
                        x=alt.X('Tipo:N', axis=None),
                        color=alt.Color('Tipo:N', scale=alt.Scale(domain=['Proyectos', 'Entregables'], range=['#FFFFFF', '#FFD700']), legend=alt.Legend(title="Tipo", labelColor="white", titleColor="white"))
                    )
                    bars = base.mark_bar(size=30, cornerRadius=5).encode(y='Total:Q')
                    text = base.mark_text(dy=-10, color='white').encode(y='Total:Q', text=alt.Text('Total:Q'))
                    chart = alt.layer(bars, text).properties(width='container', height=250).facet(column=alt.Column('Año:O', header=alt.Header(labelColor="white", titleColor="white"))).configure_view(stroke='transparent')
                    st.altair_chart(chart, width="stretch")

            st.markdown("---")
            k1, k2 = st.columns(2)
            k1.metric("Proyectos Filtrados", len(df_f))
            vis = df_f["Nombre del Proyecto"].unique()
            ev_final = (df_e_f if sg else df_e_s)[(df_e_f if sg else df_e_s)["Proyecto_Padre"].isin(vis)] if not df_e_s.empty else pd.DataFrame()
            k2.metric("Entregables Asociados", len(ev_final))

            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Por Periodo")
                data_p = df_f["Periodo"].value_counts().reset_index(); data_p.columns=["Periodo", "Total"]
                graficar_oscuro(data_p, "Periodo", "Total", "Periodo", "Total", "#FFFFFF")
            with c2:
                st.subheader("Por Categoría")
                sc = df_f["Categoría"].str.split(',').explode().str.strip(); sc=sc[sc!=""]; sc=sc[sc!="Nan"]
                data_c = sc.value_counts().reset_index(); data_c.columns=["Categoría", "Total"]
                graficar_oscuro(data_c, "Categoría", "Total", "Categoría", "Total", "#E0E0E0")

            st.markdown("---")
            st.subheader("📦 Subcategorías")
            if not ev_final.empty:
                ss = ev_final["Subcategoría"].str.split(',').explode().str.strip(); ss=ss[ss!=""]; ss=ss[ss!="Nan"]
                data_s = ss.value_counts().reset_index(); data_s.columns=["Subcategoría", "Total"]
                graficar_oscuro(data_s, "Subcategoría", "Total", "Subcategoría", "Total", "#CCCCCC")

            st.session_state.stats_download = {
                "Resumen_Anual": df_chart if 'df_chart' in locals() else pd.DataFrame(),
                "Por_Periodo": data_p if 'data_p' in locals() else pd.DataFrame(),
                "Por_Categoría": data_c if 'data_c' in locals() else pd.DataFrame(),
                "Por_Subcategoría": data_s if 'data_s' in locals() else pd.DataFrame()
            }

# ==========================================
# PESTAÑA 5: DESCARGAS
# ==========================================
with tab5:
    st.header("📥 Centro de Descargas")

    st.subheader("1. Base de Datos Completa")
    if st.button("Generar Respaldo Completo (Excel)"):
        b = io.BytesIO()
        with pd.ExcelWriter(b, engine='openpyxl') as w:
            load_data("Proyectos").to_excel(w, 'Proyectos', index=False)
            load_data("Entregables").to_excel(w, 'Entregables', index=False)
        st.download_button("⬇️ Descargar BD.xlsx", b.getvalue(), "Respaldo_Completo.xlsx")

    st.markdown("---")
    st.subheader("2. Reporte de Gráficas (Datos)")
    if "stats_download" in st.session_state and not st.session_state.stats_download.get("Resumen_Anual", pd.DataFrame()).empty:
        if st.button("Generar Reporte Estadístico"):
            b_stats = io.BytesIO()
            with pd.ExcelWriter(b_stats, engine='openpyxl') as w:
                st.session_state.stats_download["Resumen_Anual"].to_excel(w, "Resumen Anual", index=False)
                st.session_state.stats_download["Por_Periodo"].to_excel(w, "Por Periodo", index=False)
                st.session_state.stats_download["Por_Categoría"].to_excel(w, "Por Categoría", index=False)
                st.session_state.stats_download["Por_Subcategoría"].to_excel(w, "Por Subcategoría", index=False)
            st.download_button("⬇️ Descargar Reporte_Graficas.xlsx", b_stats.getvalue(), "Reporte_Graficas.xlsx")
    else:
        st.warning("⚠️ Primero ve a la pestaña 'Gráficas' para generar los datos.")

# ==========================================
# PESTAÑA 6: GLOSARIO
# ==========================================
with tab6:
    st.header("📖 Glosario de Términos")
    st.markdown("""
    ### 🗂️ Categorías
    * **Gestión:** Archivos que tengan que ver con la Dirección integral del proyecto.
    * **Comunicación:** Diseño y ejecución de mensajes, canales para alinear a internos/externos.
    * **Infraestructura:** Instalaciones fijas y móviles, planos arquitectónicos, señalética.
    * **Investigación:** História de la finca, del CEDRAM, mapeos de la zona.

    ### 📂 Subcategorías

    #### 🔹 GESTIÓN
    * **Administración:** Cronogramas, necesidades, planificación.
    * **Financiamiento:** Becas, presupuestos, donantes.
    * **Vinculación:** Contacto, relaciones públicas, alianzas.

    #### 🔹 COMUNICACIÓN
    * **Memoria/archivo CEDRAM:** Archivos de memoria del equipo del CEDRAM.
    * **Memoria/archivo PAP:** Archivos de memoria del equipo del PAP.
    * **Diseño:** Identidad visual, folletos, pósters.
    * **Difusión:** Redes sociales, campañas, impacto.

    #### 🔹 INFRAESTRUCTURA
    * **Diseño arquitectónico:** Planos, renders, conceptos.
    * **Mantenimiento:** Señalética, remodelación.
    * **Productos teatrales:** Vestuario, Kamishibai.
    """)
