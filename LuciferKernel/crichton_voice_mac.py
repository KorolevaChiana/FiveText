import threading
import subprocess

class MacVoiceModule:
    def __init__(self):
        pass

    def speak(self, text):
        if not text:
            return
        try:
            # УЛЬТИМАТУМ ИМПЕРСКОГО ШТАБА:
            # Раз мак упрямо включает девчонку на русском, мы используем мужской голос Daniel.
            # Чтобы он звучал солидно, отправляем текст напрямую через системный say с голосом Daniel.
            subprocess.run(['say', '-v', 'Daniel', text], check=True)
        except Exception as ex:
            print(f"[ОШИБКА ОЗВУЧКИ]: {ex}")

    def speak_async(self, text):
        thread = threading.Thread(target=self.speak, args=(text,))
        thread.daemon = True
        thread.start()

voice_engine = MacVoiceModule()
