import os
import zipfile
import shutil
import google.generativeai as genai
from bs4 import BeautifulSoup
import logging
import time

logging.basicConfig(
    filename='libro_proceso.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def extraer_epub(ruta_epub):
    logging.info(f"Iniciando extracción de: {ruta_epub}")
    temp_dir = "libro_temp"
    
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        with zipfile.ZipFile(ruta_epub, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            logging.info("EPUB descomprimido correctamente")
        
        texto_completo = ""
        archivos_procesados = 0
        
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.html', '.xhtml')):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                            soup = BeautifulSoup(f.read(), 'html.parser')
                            texto_completo += soup.get_text(separator=' ', strip=True) + "\n"
                            archivos_procesados += 1
                            logging.info(f"Procesado archivo {file}")
                    except Exception as e:
                        logging.error(f"Error procesando {file}: {str(e)}")
        
        logging.info(f"Procesados {archivos_procesados} archivos")
        return texto_completo
        
    except Exception as e:
        logging.error(f"Error en extracción: {str(e)}")
        raise
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

def dividir_texto(texto, max_chars=15000):
    logging.info(f"Dividiendo texto de {len(texto)} caracteres")
    texto = texto[:100000]  # Limitamos el texto para un resumen más conciso
    partes = []
    
    while texto:
        if len(texto) <= max_chars:
            partes.append(texto)
            break
        indice = texto[:max_chars].rfind('.')
        if indice == -1:
            indice = texto[:max_chars].rfind(' ')
        partes.append(texto[:indice + 1])
        texto = texto[indice + 1:].strip()
    
    logging.info(f"Texto dividido en {len(partes)} partes")
    return partes

def generar_resumen(texto):
    logging.info("Iniciando generación de resumen")
    genai.configure(api_key='AIzaSyByrGUJhQp4k4lTjh3jiOAjMrJ4De0YFcY')
    modelo = genai.GenerativeModel('gemini-pro')
    
    prompt = """
    Genera un resumen del texto en formato narrativo y fluido, como si fuera para subtítulos de video.
    Sigue estas pautas:
    - Escribe en párrafos continuos sin marcadores ni secciones
    - No uses viñetas, asteriscos ni caracteres especiales
    - No menciones capítulos, introducciones ni secciones
    - Conecta las ideas de forma natural y fluida
    - Usa un lenguaje claro y directo
    - Escribe como si estuvieras narrando una historia
    - Separa ideas solo con puntos y comas
    - El texto debe fluir naturalmente al ser leído en voz alta
    
    Texto a resumir:
    """
    
    try:
        partes = dividir_texto(texto)
        resumenes = []
        
        for i, parte in enumerate(partes, 1):
            logging.info(f"Procesando parte {i}/{len(partes)}")
            try:
                respuesta = modelo.generate_content(prompt + parte)
                resumenes.append(respuesta.text)
                logging.info(f"Parte {i} resumida correctamente")
                time.sleep(2)  # Pausa entre llamadas a la API
                
            except Exception as e:
                logging.error(f"Error en parte {i}: {str(e)}")
                continue
        
        return "\n\n".join(resumenes)
        
    except Exception as e:
        logging.error(f"Error en generación de resumen: {str(e)}")
        raise




