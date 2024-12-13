import streamlit as st
import os
from epub_extractor import extraer_epub, generar_resumen

def main():
    st.title("Extractor de Libros EPUB")
    
    # Selector de archivo EPUB
    uploaded_file = st.file_uploader("Seleccionar archivo EPUB", type=['epub'])
    
    # Nombre del archivo de salida
    output_filename = st.text_input("Nombre del archivo de salida", "resumen.txt")
    
    if st.button("Procesar"):
        if uploaded_file is None:
            st.error("Por favor, selecciona un archivo EPUB")
            return
            
        try:
            with st.spinner("Extrayendo contenido del EPUB..."):
                # Guardado temporal del archivo
                temp_path = f"temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Extracción del texto
                texto = extraer_epub(temp_path)
                
            with st.spinner("Generando resumen con IA..."):
                resumen = generar_resumen(texto)
                
            with st.spinner("Guardando resultado..."):
                # Guardar resultado
                with open(output_filename, 'w', encoding='utf-8') as f:
                    f.write(resumen)
                
            # Limpieza del archivo temporal
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
            st.success(f"¡Proceso completado! Archivo guardado como: {output_filename}")
            
            # Botón de descarga
            with open(output_filename, 'r', encoding='utf-8') as f:
                st.download_button(
                    label="Descargar resumen",
                    data=f.read(),
                    file_name=output_filename,
                    mime="text/plain"
                )
                
        except Exception as e:
            st.error(f"Error durante el procesamiento: {str(e)}")

if __name__ == "__main__":
    main()
