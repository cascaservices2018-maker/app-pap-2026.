import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import io
import time
import altair as alt # <--- IMPORTANTE: Para las gráficas bonitas

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
COLOR_FONDO_PRINCIPAL = "#A60000"  # Rojo Institucional
COLOR_BARRA_LATERAL = "#262730"    # Gris oscuro

estilos_css = f"""
<style>
    .stApp {{
        background-color: {COLOR_FONDO_PRINCIPAL};
    }}
    [data-testid="stSidebar"] {{
        background-color: {COLOR_BARRA_LATERAL};
    }}
    /* Forzar color blanco en textos de métricas y títulos para contraste */
    [data-testid="stMetricValue"], h1, h2, h3 {{
        color: white !important;
    }}
</style>
"""
st.markdown(estilos_css, unsafe_allow_html=True)

# ==========================================
# 🔗 CONFIGURACIÓN DEL SISTEMA
# ==========================================

# --- TU LOGO AQUÍ ---
LOGO_URL = "https://github.com/cascaservices2018-maker/app-pap-2026./blob/main/cedramh3-removebg-preview.png?raw=true"

# --- LISTAS FIJAS ---
CATEGORIAS_LISTA = ["Gestión", "Comunicación", "Infraestructura", "Investigación"]

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN DE CARGA INTELIGENTE (TTL=5) ---
def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=5)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        try:
            time.sleep(2)
            df = conn.read(worksheet=sheet_name, ttl=5)
            if not df.empty:
                 df.columns = df.columns.str.strip()
            return df
        except:
            st.error(f"🚨 Error de conexión. Espera un poco y recarga la página.")
            return pd.DataFrame()

def save_data(df, sheet_name):
    try:
        conn.update(worksheet=sheet_name, data=df)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"No se pudo guardar: {e}")

# --- FUNCIÓN PARA GRÁFICAS OSCURAS (ALTAIR) ---
def graficar_oscuro(df, x_col, y_col, titulo_x, titulo_y, color_barra="#FFFFFF"):
    """Crea una gráfica de barras que se ve bien en fondo rojo"""
    chart = alt.Chart(df).mark_bar(color=color_barra).encode(
        x=alt.X(x_col, title=titulo_x, sort='-y'),
        y=alt.Y(y_col, title=titulo_y),
        tooltip=[x_col, y_col]
    ).configure_axis(
        labelColor='white', # Ejes blancos
        titleColor='white', # Títulos blancos
        gridColor='#660000' # Líneas de guía rojas oscuras sutiles
    ).configure_view(
        strokeWidth=0
    ).properties(
        height=300
    )
    st.altair_chart(chart, use_container_width=True)

# --- BARRA LATERAL (SIDEBAR) ---
with st.sidebar:
    st.image(LOGO_URL, width=280) 
    st.markdown("### ⚙️ Panel de Control")
    st.info("Sistema de Gestión de Proyectos PAP - 2026")
    st.markdown("---")
    st.write("Bienvenido al sistema colaborativo.")

# --- ENCABEZADO PRINCIPAL ---
col_logo, col_titulo = st.columns([2, 8])

with col_logo:
    st.image(LOGO_URL, width=200) 
with col_titulo:
    st.title("Base de datos PAP PERIODOS 2019-2026")

st.markdown("---")

# --- PESTAÑAS DEL SISTEMA ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Registrar PROYECTO", 
    "2. Carga Masiva ENTREGABLES", 
    "3. 📝 Buscar y Editar", 
    "4. 📊 Gráficas",
    "5. 📥 Descargar Excel"
])

# ==========================================
# PESTAÑA 1: REGISTRO DE PROYECTOS
# ==========================================
with tab1:
    st.subheader("Nuevo Proyecto")
    with st.form("form_proyecto", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            anio = st.number_input("Año", min_value=2019, max_value=2030, value=datetime.now().year)
        with col2:
            periodo = st.selectbox("Periodo", ["Primavera", "Verano", "Otoño"])
        with col3:
            cats_seleccionadas = st.multiselect("Categoría(s)", CATEGORIAS_LISTA)

        nombre_proyecto = st.text_input("Nombre del Proyecto")
        descripcion = st.text_area("Descripción")
        
        c_ent, c_com = st.columns(2)
        with c_ent:
            num_entregables = st.number_input("Estimado de Entregables", min_value=1, step=1, value=1)
        with c_com:
            comentarios = st.text_area("Comentarios")

        if st.form_submit_button("💾 Guardar Proyecto"):
            if not nombre_proyecto:
                st.error("El nombre es obligatorio")
            elif not cats_seleccionadas:
                st.error("Debes elegir al menos una categoría")
            else:
                df_proy = load_data("Proyectos")
                if not df_proy.empty and "Nombre del Proyecto" in df_proy.columns and nombre_proyecto in df_proy["Nombre del Proyecto"].values:
                     st.warning("⚠️ Ya existe un proyecto con ese nombre.")
                else:
                    categoria_str = ", ".join(cats_seleccionadas)
                    nuevo = {
                        "Año": anio, "Periodo": periodo, "Nombre del Proyecto": nombre_proyecto,
                        "Descripción": descripcion, "Num_Entregables": num_entregables,
                        "Categoría": categoria_str,
                        "Comentarios": comentarios,
                        "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    df_updated = pd.concat([df_proy, pd.DataFrame([nuevo])], ignore_index=True)
                    save_data(df_updated, "Proyectos")
                    st.success("¡Proyecto guardado!")

# ==========================================
# PESTAÑA 2: CARGA MASIVA
# ==========================================
with tab2:
    st.subheader("⚡ Carga Rápida de Entregables")
    st.info("💡 **Tip:** Escribe subcategorías separadas por coma. Ej: _Diseño, Difusión_")
    
    df_p = load_data("Proyectos")
    
    if df_p.empty:
        st.warning("Cargando proyectos...")
    else:
        if "Nombre del Proyecto" in df_p.columns:
            lista_proyectos = sorted(df_p["Nombre del Proyecto"].unique().tolist())
            proyecto_sel = st.selectbox("Selecciona el Proyecto:", lista_proyectos)
            
            info_proyecto = df_p[df_p["Nombre del Proyecto"] == proyecto_sel].iloc[0]
            cat_auto = info_proyecto.get("Categoría", "General")
            num_estimado = int(info_proyecto.get("Num_Entregables", 5))
            
            st.caption(f"Categoría(s): **{cat_auto}** | Espacios generados: **{num_estimado}**")

            session_key = f"data_editor_{proyecto_sel}"

            if session_key not in st.session_state:
                st.session_state[session_key] = pd.DataFrame(
                    index=range(num_estimado), 
                    columns=["Nombre_Entregable", "Contenido", "Subcategorías", "Plantillas_Usadas"]
                )

            st.write("👇 **Llena la tabla:**")
            
            edited_df = st.data_editor(
                st.session_state[session_key],
                num_rows="dynamic",
                key=f"editor_widget_{proyecto_sel}",
                use_container_width=True, 
                column_config={
                    "Subcategorías": st.column_config.TextColumn("Subcategoría(s)", default="General"),
                    "Nombre_Entregable": st.column_config.TextColumn("Nombre Entregable", required=True),
                    "Contenido": st.column_config.TextColumn("Contenido", width="large"),
                    "Plantillas_Usadas": st.column_config.TextColumn("Link/Plantilla")
                }
            )

            if st.button("🚀 Guardar Todos los Entregables"):
                datos_validos = edited_df[edited_df["Nombre_Entregable"].notna() & (edited_df["Nombre_Entregable"] != "")].copy()
                
                if datos_validos.empty:
                    st.error("La tabla está vacía.")
                else:
                    try:
                        df_ent_cloud = load_data("Entregables")
                        nuevas_filas = []
                        fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        for index, row in datos_validos.iterrows():
                            fila = {
                                "Proyecto_Padre": proyecto_sel,
                                "Entregable": row["Nombre_Entregable"],
                                "Contenido": row["Contenido"],
                                "Categoría": cat_auto,
                                "Subcategoría": row["Subcategorías"],
                                "Plantillas": row["Plantillas_Usadas"],
                                "Fecha_Registro": fecha_hoy
                            }
                            nuevas_filas.append(fila)
                        
                        df_final = pd.concat([df_ent_cloud, pd.DataFrame(nuevas_filas)], ignore_index=True)
                        save_data(df_final, "Entregables")
                        st.success(f"¡Éxito! Se guardaron {len(nuevas_filas)} entregables.")
                        
                        del st.session_state[session_key]
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# ==========================================
# PESTAÑA 3: BUSCAR Y EDITAR
# ==========================================
with tab3:
    st.header("📝 Edición de Base de Datos")
    st.info("Haz doble clic en cualquier celda para corregirla. Al terminar, presiona el botón 'Actualizar'.")
    
    df_proy = load_data("Proyectos")
    df_ent = load_data("Entregables")

    if not df_proy.empty and "Año" in df_proy.columns:
        c1, c2 = st.columns(2)
        with c1:
            years = sorted(df_proy["Año"].unique())
            f_year = st.multiselect("Filtrar por Año:", years)
        with c2:
            f_period = st.multiselect("Filtrar por Periodo:", ["Primavera", "Verano", "Otoño"])

        df_view = df_proy.copy()
        if f_year: df_view = df_view[df_view["Año"].isin(f_year)]
        if f_period: df_view = df_view[df_view["Periodo"].isin(f_period)]

        st.subheader("1. Proyectos")
        edited_proy = st.data_editor(
            df_view,
            use_container_width=True,
            key="editor_proyectos_main",
            num_rows="fixed"
        )
        
        if st.button("💾 Actualizar Cambios en Proyectos"):
            try:
                df_master_proy = load_data("Proyectos")
                df_master_proy.update(edited_proy)
                save_data(df_master_proy, "Proyectos")
                st.success("✅ Proyectos actualizados.")
            except Exception as e:
                st.error(f"Error al actualizar: {e}")

        st.markdown("---")

        st.subheader("2. Entregables")
        if not df_ent.empty and "Proyecto_Padre" in df_ent.columns:
            visible_projects = df_view["Nombre del Proyecto"].unique()
            df_ent_view = df_ent[df_ent["Proyecto_Padre"].isin(visible_projects)]
            
            edited_ent = st.data_editor(
                df_ent_view,
                use_container_width=True,
                key="editor_entregables_main",
                num_rows="fixed",
                column_config={
                    "Subcategoría": st.column_config.TextColumn("Subcategoría"),
                    "Entregable": st.column_config.TextColumn("Nombre Entregable"),
                    "Contenido": st.column_config.TextColumn("Contenido", width="large")
                }
            )
            
            if st.button("💾 Actualizar Cambios en Entregables"):
                try:
                    df_master_ent = load_data("Entregables")
                    df_master_ent.update(edited_ent)
                    save_data(df_master_ent, "Entregables")
                    st.success("✅ Entregables actualizados.")
                except Exception as e:
                    st.error(f"Error al actualizar: {e}")
        else:
            st.info("No hay entregables para los proyectos seleccionados.")

        st.markdown("---")
        
        with st.expander("🗑️ Zona de Borrado (Peligro)"):
            st.warning("Esto borra el proyecto y TODOS sus entregables.")
            to_del = st.selectbox("Proyecto a eliminar:", df_proy["Nombre del Proyecto"].unique())
            
            if st.button("Eliminar Definitivamente"):
                df_proy_new = df_proy[df_proy["Nombre del Proyecto"] != to_del]
                if not df_ent.empty and "Proyecto_Padre" in df_ent.columns:
                    df_ent_new = df_ent[df_ent["Proyecto_Padre"] != to_del]
                    save_data(df_ent_new, "Entregables")
                
                save_data(df_proy_new, "Proyectos")
                st.success(f"Proyecto '{to_del}' eliminado.")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Cargando base de datos...")

# ==========================================
# PESTAÑA 4: GRÁFICAS (MEJORADAS PARA FONDO ROJO)
# ==========================================
with tab4:
    st.header("📊 Estadísticas en Vivo")
    try:
        df_p_s = load_data("Proyectos")
        df_e_s = load_data("Entregables")
    except:
        df_p_s = pd.DataFrame()
        df_e_s = pd.DataFrame()

    if not df_p_s.empty and "Año" in df_p_s.columns:
        st.markdown("#### Filtros")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
             years_g = st.multiselect("Año", sorted(df_p_s["Año"].unique()), default=sorted(df_p_s["Año"].unique()))
        
        with col_g2:
             all_periods = ["Primavera", "Verano", "Otoño"]
             periods_g = st.multiselect("Periodo", all_periods, default=all_periods)
        
        df_filtered = df_p_s[
            df_p_s["Año"].isin(years_g) & 
            df_p_s["Periodo"].isin(periods_g)
        ]
        
        if df_filtered.empty:
            st.warning("No hay datos.")
        else:
            st.markdown("---")
            col_kpi1, col_kpi2 = st.columns(2)
            col_kpi1.metric("Proyectos", len(df_filtered))
            
            proyectos_visibles = df_filtered["Nombre del Proyecto"].unique()
            if not df_e_s.empty and "Proyecto_Padre" in df_e_s.columns:
                df_e_filtered = df_e_s[df_e_s["Proyecto_Padre"].isin(proyectos_visibles)]
                col_kpi2.metric("Entregables", len(df_e_filtered))
            else:
                df_e_filtered = pd.DataFrame()
                col_kpi2.metric("Entregables", 0)

            st.markdown("---")
            c1, c2 = st.columns(2)
            
            with c1:
                st.subheader("Por Periodo")
                data_periodo = df_filtered["Periodo"].value_counts().reset_index()
                data_periodo.columns = ["Periodo", "Cantidad"]
                # Barras blancas para resaltar en fondo rojo
                graficar_oscuro(data_periodo, "Periodo", "Cantidad", "Periodo", "Total", "#FFFFFF")

            with c2:
                st.subheader("Por Categoría")
                if "Categoría" in df_filtered.columns:
                    series_cat = df_filtered["Categoría"].astype(str).str.split(',').explode().str.strip()
                    data_cat = series_cat.value_counts().reset_index()
                    data_cat.columns = ["Categoría", "Cantidad"]
                    # Barras gris claro
                    graficar_oscuro(data_cat, "Categoría", "Cantidad", "Categoría", "Total", "#E0E0E0")
                
            st.markdown("---")
            st.subheader("📦 Subcategorías (Desglosadas)")
            if not df_e_filtered.empty and "Subcategoría" in df_e_filtered.columns:
                 series_sub = df_e_filtered["Subcategoría"].astype(str).str.split(',').explode().str.strip()
                 data_sub = series_sub.value_counts().reset_index()
                 data_sub.columns = ["Subcategoría", "Cantidad"]
                 # Barras un poco más oscuras para variedad
                 graficar_oscuro(data_sub, "Subcategoría", "Cantidad", "Subcategoría", "Total", "#CCCCCC")
    else:
        st.info("Cargando gráficas...")

# ==========================================
# PESTAÑA 5: DESCARGAR EXCEL
# ==========================================
with tab5:
    st.header("📥 Exportar Base de Datos")
    
    if st.button("🔄 Generar Archivo Excel"):
        with st.spinner("Descargando..."):
            try:
                df_proy_down = load_data("Proyectos")
                df_ent_down = load_data("Entregables")
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_proy_down.to_excel(writer, sheet_name='Proyectos', index=False)
                    df_ent_down.to_excel(writer, sheet_name='Entregables', index=False)
                
                st.download_button(
                    label="⬇️ Descargar Excel Listo (.xlsx)",
                    data=buffer.getvalue(),
                    file_name=f"Reporte_PAP_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error: {e}")


