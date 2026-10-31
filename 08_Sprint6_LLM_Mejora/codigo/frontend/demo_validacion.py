#!/usr/bin/env python3
"""
Demo de Validación de Metadatos - Frontend Streamlit
Muestra cómo se ven las alertas de metadatos incorrectos en la UI.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../validator'))

import streamlit as st
from metadata_validator import MetadataValidator, Severity

# Configuración de página
st.set_page_config(
    page_title="Demo Validación de Metadatos",
    page_icon="🔍",
    layout="wide"
)

# CSS personalizado para las alertas
st.markdown("""
<style>
.validation-error {
    background-color: #ffebee;
    border-left: 4px solid #f44336;
    padding: 10px;
    margin: 5px 0;
    border-radius: 4px;
}
.validation-warning {
    background-color: #fff3e0;
    border-left: 4px solid #ff9800;
    padding: 10px;
    margin: 5px 0;
    border-radius: 4px;
}
.validation-info {
    background-color: #e3f2fd;
    border-left: 4px solid #2196f3;
    padding: 10px;
    margin: 5px 0;
    border-radius: 4px;
}
.dataset-card {
    background-color: #f5f5f5;
    padding: 20px;
    border-radius: 8px;
    margin: 10px 0;
}
.metric-badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
    margin-right: 5px;
}
.badge-error { background-color: #ffebee; color: #c62828; }
.badge-warning { background-color: #fff3e0; color: #ef6c00; }
.badge-success { background-color: #e8f5e9; color: #2e7d32; }
</style>
""", unsafe_allow_html=True)

def severity_icon(severity):
    """Retorna icono según severidad."""
    icons = {
        Severity.CRITICAL: "🔴",
        Severity.ERROR: "❌",
        Severity.WARNING: "⚠️",
        Severity.INFO: "ℹ️"
    }
    return icons.get(severity, "⚪")

def severity_color(severity):
    """Retorna clase CSS según severidad."""
    colors = {
        Severity.CRITICAL: "validation-error",
        Severity.ERROR: "validation-error",
        Severity.WARNING: "validation-warning",
        Severity.INFO: "validation-info"
    }
    return colors.get(severity, "validation-info")

# Inicializar validador
@st.cache_resource
def get_validator():
    return MetadataValidator().add_default_rules()

validator = get_validator()

# Sidebar con información
st.sidebar.title("🔧 Panel de Control")
st.sidebar.markdown("---")

modo = st.sidebar.radio(
    "Seleccionar modo:",
    ["Ver ejemplos predefinidos", "Crear dataset personalizado"]
)

st.sidebar.markdown("---")
st.sidebar.info("""
**Tipos de validación:**
- ✅ **Campos obligatorios**: Título, publisher, tema
- ⚠️ **Consistencia cruzada**: Título vs Publisher
- ⚠️ **Formato**: Valores estándar
""")

# Título principal
st.title("🔍 Demo: Validación de Metadatos de Datasets")
st.markdown("Este demo muestra cómo el sistema detecta **errores de metadatos** como el caso UEx/Barcelona.")

if modo == "Ver ejemplos predefinidos":
    st.header("📚 Ejemplos Predefinidos")

    # Dataset con error UEx/Barcelona
    st.subheader("Caso 1: Error de federación UEx ↔ Barcelona")

    dataset_error_uex = {
        "dataset_id": "datosgob-u00200001-proyectos",
        "title": "Portal de investigación de la Universidad de Extremadura",
        "description": "Proyectos de investigación activos en la UEx (Universidad de Extremadura). Datos de grupos de investigación.",
        "publisher": "Universidad de Barcelona",  # ERROR!
        "territory": "Cataluña",  # ERROR!
        "theme": "investigacion",
        "format": "JSON",
        "url": "https://opendata.unex.es/dataset/proyectos"
    }

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Dataset:**")
        st.json(dataset_error_uex)

    with col2:
        st.markdown("**Validación:**")
        issues = validator.validate_dataset(dataset_error_uex)

        if issues:
            for issue in issues:
                css_class = severity_color(issue.severity)
                icon = severity_icon(issue.severity)
                st.markdown(f"""
                <div class="{css_class}">
                    <b>{icon} {issue.severity.value.upper()}</b><br>
                    <b>Campo:</b> {issue.field}<br>
                    {issue.message}<br>
                    <small>💡 {issue.suggestion}</small>
                </div>
                """, unsafe_allow_html=True)

            # Mostrar contexto si existe
            for issue in issues:
                if issue.context:
                    with st.expander("🔍 Ver detalles técnicos"):
                        st.json(issue.context)
        else:
            st.success("✅ No se detectaron problemas")

    st.markdown("---")

    # Dataset con campos vacíos
    st.subheader("Caso 2: Campos obligatorios vacíos")

    dataset_vacio = {
        "dataset_id": "dataset-incompleto-001",
        "title": "",
        "description": "   ",
        "publisher": None,
        "territory": "",
        "theme": "desconocido",
        "format": "CSV"
    }

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Dataset:**")
        st.json(dataset_vacio)

    with col2:
        st.markdown("**Validación:**")
        issues = validator.validate_dataset(dataset_vacio)

        if issues:
            for issue in issues:
                css_class = severity_color(issue.severity)
                icon = severity_icon(issue.severity)
                st.markdown(f"""
                <div class="{css_class}">
                    <b>{icon} {issue.severity.value.upper()}</b><br>
                    <b>Campo:</b> {issue.field}<br>
                    {issue.message}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Sin problemas")

    st.markdown("---")

    # Dataset correcto
    st.subheader("Caso 3: Dataset correcto ✅")

    dataset_correcto = {
        "dataset_id": "ine-empleo-2024",
        "title": "Estadísticas de empleo por comunidades autónomas",
        "description": "Tasa de paro y empleo desagregada por CCAA",
        "publisher": "Instituto Nacional de Estadística",
        "territory": "España",
        "theme": "empleo",
        "format": "CSV"
    }

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Dataset:**")
        st.json(dataset_correcto)

    with col2:
        st.markdown("**Validación:**")
        issues = validator.validate_dataset(dataset_correcto)

        if issues:
            for issue in issues:
                css_class = severity_color(issue.severity)
                icon = severity_icon(issue.severity)
                st.markdown(f"""
                <div class="{css_class}">
                    <b>{icon} {issue.severity.value.upper()}</b><br>
                    {issue.message}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Dataset válido - Sin problemas detectados")

    st.markdown("---")

    # Caso adicional: Abreviatura CSIC mal asignada
    st.subheader("Caso 4: Abreviatura CSIC mal asignada")

    dataset_csic = {
        "dataset_id": "csic-pub-2024",
        "title": "Publicaciones científicas CSIC 2024",
        "description": "Repositorio de papers del Consejo Superior de Investigaciones Científicas",
        "publisher": "Universidad de Granada",  # ERROR - debería ser CSIC
        "territory": "Andalucía",
        "theme": "ciencia",
        "format": "JSON"
    }

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("**Dataset:**")
        st.json(dataset_csic)

    with col2:
        st.markdown("**Validación:**")
        issues = validator.validate_dataset(dataset_csic)

        if issues:
            for issue in issues:
                css_class = severity_color(issue.severity)
                icon = severity_icon(issue.severity)
                st.markdown(f"""
                <div class="{css_class}">
                    <b>{icon} {issue.severity.value.upper()}</b><br>
                    <b>Campo:</b> {issue.field}<br>
                    {issue.message}<br>
                    <small>💡 {issue.suggestion}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ Sin problemas")

else:
    # Modo personalizado
    st.header("✏️ Crear Dataset Personalizado")

    st.markdown("Crea tu propio dataset y valida sus metadatos:")

    col1, col2 = st.columns(2)

    with col1:
        dataset_id = st.text_input("ID del dataset", "mi-dataset-001")
        title = st.text_area("Título", "Proyectos de investigación UEx")
        description = st.text_area("Descripción", "Datos de la Universidad de Extremadura")

    with col2:
        publisher = st.text_input("Publisher", "Universidad de Barcelona")
        territory = st.selectbox(
            "Territorio",
            ["", "España", "Extremadura", "Cataluña", "Andalucía",
             "Madrid", "País Vasco", "Galicia", "Otro"]
        )
        theme = st.text_input("Tema", "investigacion")
        format = st.selectbox("Formato", ["", "CSV", "JSON", "XML", "PDF", "Otro"])

    if st.button("🔍 Validar Dataset", type="primary"):
        dataset_personalizado = {
            "dataset_id": dataset_id,
            "title": title,
            "description": description,
            "publisher": publisher,
            "territory": territory,
            "theme": theme,
            "format": format
        }

        st.markdown("---")
        st.subheader("Resultado de la Validación")

        issues = validator.validate_dataset(dataset_personalizado)

        # Contar por severidad
        critical_count = len([i for i in issues if i.severity == Severity.CRITICAL])
        error_count = len([i for i in issues if i.severity == Severity.ERROR])
        warning_count = len([i for i in issues if i.severity == Severity.WARNING])

        # Métricas
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.metric("Críticos", critical_count, delta=None)
        with col_m2:
            st.metric("Errores", error_count, delta=None)
        with col_m3:
            st.metric("Advertencias", warning_count, delta=None)
        with col_m4:
            status = "❌ Con problemas" if issues else "✅ Válido"
            st.metric("Estado", status)

        st.markdown("---")

        if issues:
            st.error(f"Se encontraron {len(issues)} problemas en los metadatos")

            for issue in issues:
                css_class = severity_color(issue.severity)
                icon = severity_icon(issue.severity)
                st.markdown(f"""
                <div class="{css_class}">
                    <b>{icon} [{issue.rule_id}] {issue.severity.value.upper()}</b><br>
                    <b>Campo afectado:</b> <code>{issue.field}</code><br>
                    {issue.message}<br>
                    <small>💡 {issue.suggestion}</small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ ¡Excelente! El dataset tiene metadatos válidos y consistentes.")
            st.balloons()

# Footer
st.markdown("---")
st.caption("Demo del Sistema de Validación de Metadatos - Fase 08 Sprint 6")
