import os
import subprocess
import sys

def transcribe_audio_whisper(audio_path, model_size="base"):
    """
    Имперский мастер распознавания аудиофайлов в текст с помощью OpenAI Whisper.
    Работает локально на macOS, поддерживает .mp3, .wav, .m4a, .ogg.
    """
    if not os.path.exists(audio_path):
        print(f"[ОШИБКА] Аудиофайл не найден: {audio_path}")
        return None

    print(f"[МАСТЕР АУДИО-ДОПРОСА] Запуск локального дознания через Whisper (модель: {model_size})...")
    
    try:
        import whisper
    except ImportError:
        print("[МОБИЛИЗАЦИЯ] Библиотека 'openai-whisper' не найдена. Устанавливаем через pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "openai-whisper"], check=True)
        import whisper

    try:
        model = whisper.load_model(model_size)
        print(f"[ДОПРОС] Расшифровываем аудиодорожку: {audio_path}...")
        result = model.transcribe(audio_path, language="ru")
        
        transcript_text = result.get("text", "").strip()
        print(f"[УСПЕХ] Аудио-пленник расколот! Извлечено символов: {len(transcript_text)}")
        return transcript_text
    except Exception as e:
        print(f"[ОШИБКА РАСШИФРОВКИ WHISPER]: {e}")
        return None

if __name__ == "__main__":
    print("Имперский модуль транскрипции аудио готов к боевому применению.")
