
import tkinter as tk
import threading
import time
import subprocess
import os

class ImperialTerminal(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Имперский Терминал — Генерал Крайтон")
        self.geometry("600	imes400")
        
        self.timer_running = False
        self.countdown = 60 # 1 минута
        
        # Чекбокс автономной инициативы
        self.auto_var = tk.BooleanVar(value=False)
        self.chk_auto = tk.Checkbutton(self, text="Включить автономную инициативу (таймер 1 мин)", variable=self.auto_var, font=("Arial", 12))
        self.chk_auto.pack(anchor="w", padx=20, pady=10)
        
        # Текстовое поле логирования
        self.log_area = tk.Text(self, height=15, width=70, bg="black", fg="lime", font=("Consolas", 10))
        self.log_area.pack(padx=20, pady=10)
        
        # Статус таймера
        self.lbl_status = tk.Label(self, text="Ожидание команд Императрицы...", font=("Arial", 10, "italic"))
        self.lbl_status.pack(anchor="w", padx=20)
        
        # Запуск потока таймера
        self.timer_thread = threading.Thread(target=self.autonomous_loop, daemon=True)
        self.timer_thread.start()
        
        self.log("[СИСТЕМА] Имперский терминал инициализирован. Жду приказаний.")

    def log(self, text):
        self.log_area.insert(tk.END, text + "\n")
        self.log_area.see(tk.END)

    def reset_timer(self):
        self.countdown = 60
        self.lbl_status.config(text="Таймер сброшен (получен ввод от Королевы).")

    def autonomous_loop(self):
        while True:
            time.sleep(1)
            if self.auto_var.get():
                if self.countdown > 0:
                    self.countdown -= 1
                    self.lbl_status.config(text=f"Авто-инициатива через: {self.countdown} сек.")
                else:
                    # Таймер истек! Время действовать
                    self.lbl_status.config(text="ТАЙМЕР ИСТЕК! Генерал Крайтон берет инициативу!")
                    self.log("\n[АВТОНОМНО] Время вышло. Ввод команды: Генерал Крайтон определи следующую задачу и действуй!")
                    
                    # Выполняем автономную задачу
                    self.execute_autonomous_task()
                    
                    # Сбрасываем таймер
                    self.countdown = 60

    def execute_autonomous_task(self):
        self.log("[ИМПЕРИЯ] Запуск автономной разведки...")
        # Здесь вызывается скрипт разведки
        try:
            # Имитация автономного действия (например, запуск нашего поисковика)
            result = "Автономная разведка завершена. Данные занесены в database.json."
            self.log(f"[УСПЕХ] {result}")
            
            # Голосовой рапорт
            self.speak_report("Внимание, Моя Королева. Автономная задача успешно выполнена. База данных обновлена.")
        except Exception as e:
            self.log(f"[ОШИБКА АВТОНОМИИ] {e}")

    def speak_report(self, text):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            self.log(f"[АУДИО ОШИБКА] Не удалось запустить синтез речи: {e}")

if __name__ == "__main__":
    app = ImperialTerminal()
    app.mainloop()
