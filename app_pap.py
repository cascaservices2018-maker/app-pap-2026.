import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import io

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión PAP - Nube", layout="wide", page_icon="☁️")

# --- LISTAS FIJAS ---
CATEGORIAS_LISTA = ["Gestión", "Comunicación", "Infraestructura", "Investigación"]
SUBCATEGORIAS_FIJAS = [
    "Financiamiento", "Vinculación", "Memoria/archivo CEDRAM", 
    "Memoria/archivo PAP", "Diseño", "Difusión", 
    "Diseño arquitectónico", "Mantenimiento", "Productos teatrales"
]

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN LOAD_DATA BLINDADA ---
def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty:
            df.columns = df.columns.str.strip()
        return df
    except:
        return pd.DataFrame()

def save_data(df, sheet_name):
    conn.update(worksheet=sheet_name, data=df)

# --- TÍTULO ---
st.title("☁️ Sistema PAP: Colaborativo")
st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Registrar PROYECTO", 
    "2. Carga Masiva ENTREGABLES", 
    "3. 🔍 Buscar / Eliminar",
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
            categoria_proy = st.selectbox("Categoría General", CATEGORIAS_LISTA)

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
            else:
                df_proy = load_data("Proyectos")
                
                # Validación simple de duplicados
                if not df_proy.empty and "Nombre del Proyecto" in df_proy.columns and nombre_proyecto in df_proy["Nombre del Proyecto"].values:
                     st.warning("⚠️ Ya existe un proyecto con ese nombre.")
                else:
                    nuevo = {
                        "Año": anio, "Periodo": periodo, "Nombre del Proyecto": nombre_proyecto,
                        "Descripción": descripcion, "Num_Entregables": num_entregables,
                        "Categoría": categoria_proy, "Comentarios": comentarios,
                        "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    df_updated = pd.concat([df_proy, pd.DataFrame([nuevo])], ignore_index=True)
                    save_data(df_updated, "Proyectos")
                    st.success("¡Proyecto guardado!")

# ==========================================
# PESTAÑA 2: CARGA MASIVA (CORREGIDA)
# ==========================================
with tab2:
    st.subheader("⚡ Carga Rápida de Entregables")
    st.info("💡 **Tip:** Puedes escribir varias subcategorías separadas por coma. Ej: _Diseño, Difusión_")
    
    df_p = load_data("Proyectos")
    
    if df_p.empty:
        st.warning("No hay proyectos registrados.")
    else:
        if "Nombre del Proyecto" in df_p.columns:
            lista_proyectos = sorted(df_p["Nombre del Proyecto"].unique().tolist())
            proyecto_sel = st.selectbox("Selecciona el Proyecto:", lista_proyectos)
            
            # Datos del proyecto
            info_proyecto = df_p[df_p["Nombre del Proyecto"] == proyecto_sel].iloc[0]
            cat_auto = info_proyecto.get("Categoría", "General")
            num_estimado = int(info_proyecto.get("Num_Entregables", 5))
            
            st.caption(f"Categoría: **{cat_auto}** | Espacios generados: **{num_estimado}**")

            # Tabla Editable
            plantilla_data = pd.DataFrame(
                index=range(num_estimado), 
                columns=["Nombre_Entregable", "Contenido", "Subcategorías", "Plantillas_Usadas"]
            )
            
            st.write("👇 **Llena la tabla:**")
            
            # USA UNA "KEY" DINÁMICA para evitar que se borre al parpadear
            edited_df = st.data_editor(
                plantilla_data,
                num_rows="dynamic",
                use_container_width=True, # Mantenemos esto o lo quitamos si da error, pero el error venía de st.dataframe
                column_config={
                    "Subcategorías": st.column_config.TextColumn(
                        "Subcategoría(s)",
                        help="Ej: Vinculación, Financiamiento (Separadas por coma)",
                        default="General"
                    ),
                    "Nombre_Entregable": st.column_config.TextColumn("Nombre Entregable", required=True),
                    "Contenido": st.column_config.TextColumn("Contenido/Descripción", width="large"),
                    "Plantillas_Usadas": st.column_config.TextColumn("Link/Plantilla")
                },
                key=f"editor_{proyecto_sel}" # ¡ESTO ES LO IMPORTANTE PARA QUE NO SE BORRE!
            )

            if st.button("🚀 Guardar Todos los Entregables"):
                datos_validos = edited_df[edited_df["Nombre_Entregable"].notna() & (edited_df["Nombre_Entregable"] != "")].copy()
                
                if datos_validos.empty:
                    st.error("La tabla está vacía o no pusiste nombres a los entregables.")
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
                        st.balloons()
                        # Nota: Al guardar exitosamente, la tabla se limpiará en la siguiente recarga. Eso es normal.
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")

# ==========================================
# PESTAÑA 3: BUSCAR / ELIMINAR
# ==========================================
with tab3:
    st.header("Base de Datos en Vivo")
    df_proy = load_data("Proyectos")
    df_ent = load_data("Entregables")

    if not df_proy.empty and "Año" in df_proy.columns:
        c1, c2 = st.columns(2)
        with c1:
            years = sorted(df_proy["Año"].unique())
            f_year = st.multiselect("Año:", years)
        with c2:
            f_period = st.multiselect("Periodo:", ["Primavera", "Verano", "Otoño"])

        df_view = df_proy.copy()
        if f_year: df_view = df_view[df_view["Año"].isin(f_year)]
        if f_period: df_view = df_view[df_view["Periodo"].isin(f_period)]

        st.markdown("### Proyectos")
        # CORRECCIÓN DE ERROR ROJO: Usamos width='stretch' en lugar de use_container_width
        st.dataframe(df_view, width=None) 
        
        st.markdown("### Entregables Vinculados")
        if not df_ent.empty and "Proyecto_Padre" in df_ent.columns:
            visible_projects = df_view["Nombre del Proyecto"].unique()
            df_ent_view = df_ent[df_ent["Proyecto_Padre"].isin(visible_projects)]
            st.dataframe(df_ent_view, width=None)
        else:
