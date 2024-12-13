
import moviepy.config as conf
conf.IMAGEMAGICK_BINARY = r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"

from PIL import Image
Image.ANTIALIAS = Image.Resampling.LANCZOS

import os
import logging
import traceback
import psutil
import gc

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_credentials.json"

from google.cloud import texttospeech
from moviepy.editor import AudioFileClip, TextClip, VideoFileClip, CompositeVideoClip, concatenate_videoclips, concatenate_audioclips
import glob
import random

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
    'es-ES-Standard-C': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Standard-D': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Standard-E': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Standard-F': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Studio-C': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Studio-F': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Wavenet-B': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Wavenet-C': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Wavenet-D': texttospeech.SsmlVoiceGender.FEMALE,
    'es-ES-Wavenet-E': texttospeech.SsmlVoiceGender.MALE,
    'es-ES-Wavenet-F': texttospeech.SsmlVoiceGender.FEMALE
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_generator.log'),
        logging.StreamHandler()
    ]
)

def dividir_texto(texto, max_chars=4800):
    try:
        partes = []
        while len(texto) > max_chars:
            indice = texto[:max_chars].rfind('.')
            if indice == -1:
                indice = texto[:max_chars].rfind(' ')
            if indice == -1:
                raise ValueError(f"No se encontró un punto o espacio para dividir el texto")
            partes.append(texto[:indice + 1])
            texto = texto[indice + 1:].strip()
        if texto:
            partes.append(texto)
        logging.info(f"Texto dividido en {len(partes)} partes")
        return partes
    except Exception as e:
        logging.error(f"Error al dividir texto: {str(e)}")
        raise

def validar_video(video_path):
    try:
        clip = VideoFileClip(video_path, audio=False, target_resolution=(360, None))
        if clip.duration <= 0:
            clip.close()
            return False
        frame = clip.get_frame(0)
        clip.close()
        return True if frame is not None else False
    except:
        logging.warning(f"Video no válido: {video_path}")
        return False

def crear_video(texto, carpeta_videos, nombre_salida="video_final.mp4", duracion_clip=15, voz_seleccionada="es-ES-Standard-A", selected_clips=None):
    archivos_audio_temp = []
    clips_finales = []
    
    try:
        logging.info(f"Iniciando creación de video: {nombre_salida}")
        logging.info(f"Longitud del texto: {len(texto)} caracteres")
        
        partes_texto = dividir_texto(texto)
        
        # Generar audio
        logging.info("Generando audio...")
        for i, parte in enumerate(partes_texto):
            logging.info(f"Procesando parte de audio {i+1} de {len(partes_texto)}")
            client = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=parte)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code="es-ES",
                name=voz_seleccionada,
                ssml_gender=VOCES_DISPONIBLES.get(voz_seleccionada, texttospeech.SsmlVoiceGender.FEMALE)
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=0.9,
                pitch=0
            )
            
            response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            
            archivo_temp = f"audio_temp_{i}.mp3"
            with open(archivo_temp, "wb") as out:
                out.write(response.audio_content)
            archivos_audio_temp.append(archivo_temp)

        # Procesar audio
        logging.info("Combinando archivos de audio...")
        clips_audio = [AudioFileClip(archivo) for archivo in archivos_audio_temp]
        audio_final = concatenate_audioclips(clips_audio)
        duracion_total = audio_final.duration
        logging.info(f"Duración total del audio: {duracion_total} segundos")
        
        for clip in clips_audio:
            clip.close()

        # Preparar videos
        logging.info("Preparando videos...")
        videos = selected_clips if selected_clips else glob.glob(os.path.join(carpeta_videos, "*.mp4"))
        videos = [v for v in videos if validar_video(v)]
        
        if not videos:
            raise Exception("No se encontraron videos válidos")
        logging.info(f"Videos válidos encontrados: {len(videos)}")

        # Procesar frases
        frases = []
        for parte in partes_texto:
            frases.extend([f.strip() for f in parte.split('.') if f.strip()])
        
        tiempo_por_frase = duracion_total / len(frases)
        
        # Procesar video
        total_frases = len(frases)
        logging.info(f"Iniciando procesamiento de {total_frases} frases...")
        
        TAMAÑO_LOTE = 2
        for i in range(0, total_frases, TAMAÑO_LOTE):
            lote_actual = frases[i:i + TAMAÑO_LOTE]
            clips_lote = []
            
            for j, frase in enumerate(lote_actual):
                video_path = random.choice(videos)
                logging.info(f"Procesando frase {i+j+1} de {total_frases} ({((i+j+1)/total_frases)*100:.1f}%)")
                
                video_clip = VideoFileClip(video_path, audio=False, target_resolution=(360, None))
                
                if video_clip.duration < tiempo_por_frase:
                    video_clip = video_clip.loop(duration=tiempo_por_frase)
                else:
                    inicio = random.uniform(0, max(0, video_clip.duration - tiempo_por_frase))
                    video_clip = video_clip.subclip(inicio, inicio + tiempo_por_frase)
                
                texto_clip = (TextClip(frase, fontsize=30, color='white', bg_color='rgba(0,0,0,0.8)',
                                     size=(video_clip.w * 0.9, None), method='caption',
                                     align='center', font='Arial')
                            .set_duration(tiempo_por_frase)
                            .set_position(('center', 0.85), relative=True))
                
                clip_compuesto = CompositeVideoClip([video_clip, texto_clip]).set_duration(tiempo_por_frase)
                clips_lote.append(clip_compuesto)
                
                video_clip.close()
                texto_clip.close()
            
            if clips_lote:
                logging.info(f"Uniendo lote {(i//TAMAÑO_LOTE)+1} de {(total_frases + TAMAÑO_LOTE - 1)//TAMAÑO_LOTE}")
                clip_unido = concatenate_videoclips(clips_lote, method="compose")
                clips_finales.append(clip_unido)
                
                for clip in clips_lote:
                    clip.close()
            
            gc.collect()

        # Crear video final
        if clips_finales:
            logging.info("Generando video final...")
            video_final = concatenate_videoclips(clips_finales, method="compose")
            video_final = video_final.set_audio(audio_final)
            
            logging.info("Guardando video final...")
            video_final.write_videofile(
                nombre_salida,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                preset='ultrafast',
                audio_bitrate="192k"
            )
            
            video_final.close()
            logging.info("Video creado exitosamente")
            
    finally:
        logging.info("Limpiando archivos temporales...")
        for archivo in archivos_audio_temp:
            if os.path.exists(archivo):
                try:
                    os.remove(archivo)
                    logging.info(f"Archivo temporal eliminado: {archivo}")
                except Exception as e:
                    logging.error(f"Error eliminando archivo temporal: {str(e)}")
        
        for clip in clips_finales:
            try:
                clip.close()
            except:
                pass
        
        gc.collect()
        logging.info("Proceso finalizado")
