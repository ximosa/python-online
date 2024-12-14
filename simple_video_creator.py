import os
import json
import streamlit as st
from google.cloud import texttospeech
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import logging
import time

logging.basicConfig(level=logging.INFO)

# Configuración de credenciales
credentials = dict(st.secrets.gcp_service_account)
with open("google_credentials.json", "w") as f:
    json.dump(credentials, f)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"

VOCES_DISPONIBLES = {
    'es-ES-Journey-D': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Journey-F': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Journey-O': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Neural2-A': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Neural2-B': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Neural2-C': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Neural2-D': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Neural2-E': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Neural2-F': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Polyglot-1': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Standard-A': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Standard-B': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Standard-C': texttospeech.SsmlVoiceGender.FEMALE
}

def create_text_image(text, size=(1280, 360), font_size=30, line_height = 40): #Ajustamos
    img = Image.new('RGB', size, 'black')
    draw = ImageDraw.Draw(img)
    # Usamos DejaVu que tiene buen soporte para caracteres españoles
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        test_line = ' '.join(current_line)
        left, top, right, bottom = draw.textbbox((0, 0), test_line, font=font)
        if right > size[0] - 60:
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))
    
    total_height = len(lines) * line_height
    y = (size[1] - total_height) // 2
    
    for line in lines:
        left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
        x = (size[0] - (right - left)) // 2
        draw.text((x, y), line, font=font, fill="white")
        y += line_height
    
    return np.array(img)

def get_word_timings(text, audio_duration):
    words = text.split()
    num_words = len(words)
    duration_per_word = audio_duration / num_words if num_words > 0 else 0
    
    timings = []
    start_time = 0
    for word in words:
        end_time = start_time + duration_per_word
        timings.append({"palabra": word, "inicio": start_time, "fin": end_time})
        start_time = end_time
        
    return timings
    
def create_video(texto, nombre_salida, voz, velocidad, pausa_duracion):
    archivos_temp = []
    clips_audio = []
    clips_finales = []
    
    try:
        logging.info("Iniciando proceso de creación de video...")
        
        client = texttospeech.TextToSpeechClient()
        
        synthesis_input = texttospeech.SynthesisInput(text=texto)
        voice = texttospeech.VoiceSelectionParams(
            language_code="es-ES",
            name=voz,
            ssml_gender=VOCES_DISPONIBLES[voz]
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        
        retry_count = 0
        max_retries = 3
        
        while retry_count <= max_retries:
          try:
            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            break
          except Exception as e:
              logging.error(f"Error al solicitar audio (intento {retry_count + 1}): {str(e)}")
              if "429" in str(e):
                retry_count +=1
                time.sleep(2**retry_count) #Backoff exponencial
                
              else:
                raise 
        
        if retry_count > max_retries:
            raise Exception("Maximos intentos de reintento alcanzado")
        
        
        temp_filename = f"temp_audio.mp3"
        archivos_temp.append(temp_filename)
        with open(temp_filename, "wb") as out:
            out.write(response.audio_content)
        
        audio_clip = AudioFileClip(temp_filename)
        clips_audio.append(audio_clip)
        duracion = audio_clip.duration

        audio_clip_velocidad = audio_clip.speedx(velocidad)
    
        # Reemplaza marcadores de pausa por pausas en el audio
        segmentos_audio = []
        texto_segmentos = []
        segmento_actual_texto = ""
        segmento_actual_audio = audio_clip_velocidad
    
        for segmento in texto.split("[PAUSA]"):
            texto_segmentos.append(segmento)
            if segmento_actual_audio is not None:
              segmentos_audio.append(segmento_actual_audio)

              if len(segmentos_audio) < len(texto.split("[PAUSA]")):
                segmento_actual_audio = AudioFileClip(temp_filename).set_start(audio_clip.duration + pausa_duracion).speedx(velocidad) #Crea un clip vacío con la duracion necesaria
              else:
                segmento_actual_audio = None

        audio_final = concatenate_audioclips(segmentos_audio)
        palabras_tiempo = get_word_timings(texto, audio_final.duration)

        img_clip = ImageClip(create_text_image(texto))
        
        txt_clip = (img_clip
                      .set_start(0)
                      .set_duration(audio_final.duration)
                      .set_position('center'))
        
        video_segment = txt_clip.set_audio(audio_final)
        clips_finales.append(video_segment)
            
        
        video_final = concatenate_videoclips(clips_finales, method="compose")
        
        video_final.write_videofile(
            nombre_salida,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            preset='ultrafast',
            threads=4
        )
        
        video_final.close()
        
        for clip in clips_audio:
            clip.close()
        
        for clip in clips_finales:
            clip.close()
            
        for temp_file in archivos_temp:
            try:
                if os.path.exists(temp_file):
                    os.close(os.open(temp_file, os.O_RDONLY))
                    os.remove(temp_file)
            except:
                pass

        return True, "Video generado exitosamente",palabras_tiempo, temp_filename
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        for clip in clips_audio:
            try:
                clip.close()
            except:
                pass
                
        for clip in clips_finales:
            try:
                clip.close()
            except:
                pass
                
        for temp_file in archivos_temp:
            try:
                if os.path.exists(temp_file):
                    os.close(os.open(temp_file, os.O_RDONLY))
                    os.remove(temp_file)
            except:
                pass
        
        return False, str(e), None,None


# Streamlit UI
st.title("Generador de Videos con Controles")
texto = st.text_area("Introduce el texto (usa [PAUSA] para pausas)", "Este es un ejemplo de texto. [PAUSA] con una pausa de 1 segundo.")
nombre_salida = st.text_input("Nombre del archivo de salida", "video_con_controles.mp4")
voz_seleccionada = st.selectbox("Selecciona una voz", list(VOCES_DISPONIBLES.keys()))
velocidad = st.slider("Velocidad de Narración", 0.5, 2.0, 1.0, 0.1)
pausa_duracion = st.slider("Duración de la pausa", 0, 2, 1,1)

if st.button("Generar y Reproducir"):
    if texto and nombre_salida and voz_seleccionada:
        estado, mensaje, palabras_tiempo,temp_filename = create_video(texto, nombre_salida, voz_seleccionada, velocidad, pausa_duracion)
        if estado:
            st.success(mensaje)
            st.video(nombre_salida)

            audio_clip = AudioFileClip(temp_filename)
            texto_container = st.empty() #Contenedor para el texto
            start = time.time()

            for word_info in palabras_tiempo:
              current_time = time.time() - start
              if current_time >= word_info["inicio"]:
                texto_resaltado = ""
                for info in palabras_tiempo:
                  if current_time >= info["inicio"] and current_time <= info["fin"]:
                     texto_resaltado += f'<span style="background-color: yellow;">{info["palabra"]}</span> '
                  else:
                    texto_resaltado += f'{info["palabra"]} '
                texto_container.markdown(f'<p style="font-size:20px;">{texto_resaltado}</p>',unsafe_allow_html=True)
              time.sleep(0.01)
            audio_clip.close()
            try:
              if os.path.exists(temp_filename):
                 os.close(os.open(temp_filename, os.O_RDONLY))
                 os.remove(temp_filename)
            except:
              pass
        else:
          st.error(f"Error al generar el video: {mensaje}")
    else:
        st.warning("Por favor, ingresa el texto, el nombre del archivo y selecciona una voz.")







