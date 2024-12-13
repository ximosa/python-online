import streamlit as st
import os
from simple_video_creator import create_simple_video, VOCES_DISPONIBLES

st.title("Generador de Videos con Texto y Audio")

uploaded_file = st.file_uploader("Subir archivo de texto (.txt)", type=['txt'])
texto = ""

if uploaded_file:
    texto = uploaded_file.getvalue().decode("utf-8")
    st.text_area("Contenido del texto:", value=texto, height=200)

voz_seleccionada = st.selectbox(
    "Selecciona una voz:",
    options=list(VOCES_DISPONIBLES.keys()),
    format_func=lambda x: f"{x}"
)

nombre_salida = st.text_input("Nombre del archivo:", value="video_salida.mp4")

if st.button("Generar Video"):
    if not texto:
        st.warning("Por favor, sube un archivo de texto primero")
    else:
        with st.spinner('Generando video...'):
            success, mensaje = create_simple_video(texto, nombre_salida, voz_seleccionada)
            if success:
                st.success(mensaje)
                with open(nombre_salida, 'rb') as file:
                    st.download_button(
                        label="⬇️ Descargar Video",
                        data=file,
                        file_name=nombre_salida,
                        mime='video/mp4'
                    )
            else:
                st.error(f"Error en la generación del video: {mensaje}")

