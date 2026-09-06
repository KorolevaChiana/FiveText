import subprocess
import threading

class MacVoiceModule:
    # Устанавливаем суровый мужской голос "Yuri" по умолчанию
    def __init__(self, default_voice="Yuri"):
        self.default_voice = default_voice

    def speak(self, text):
        """ Синхронный вызов озвучки через macOS say """
        if not text:
            return
        try:
            # Пробуем озвучить выбранным мужским голосом
            subprocess.run(['say', '-v', self.default_voice, text], check=True)
        except Exception as e:
            # Если голос Юрий не скачан, ПИШЕМ ОБ ЭТОМ В КОНСОЛЬ и бьем резервом
            print(f"\n[ВНИМАНИЕ! КРАЙТОН-ВОКАЛИЗАТОР]: Голос '{self.default_voice}' не найден в macOS!")
            print(f"Причина: {e}")
            print(f"Переключаюсь на стандартный (женский) системный голос...\n")
            try:
                subprocess.run(['say', text], check=True)
            except Exception as ex:
                print(f"[ОШИБКА ГОЛОСА ВООБЩЕ]: {ex}")

    def speak_async(self, text):
        """ Асинхронный запуск в фоновом потоке, чтобы не морозить интерфейс """
        thread = threading.Thread(target=self.speak, args=(text,))
        thread.daemon = True
        thread.start()

# Глобальный экземпляр модуля
voice_engine = MacVoiceModule()

# Обертка для прямого вызова из SuperKrayton.py
def speak_async(text):
    voice_engine.speak_async(text)

if __name__ == "__main__":
    speak_async("Моя Королева, если голос женский, значит Юрий все еще не скачан в настройках.")
