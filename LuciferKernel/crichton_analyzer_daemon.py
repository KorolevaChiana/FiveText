import os
import sys
import threading
import time
import sqlite3
import requests
import json
import base64
import zlib
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

PROXY_URL = "http://92.61.71.68:49215/chat"
DB_NAME = "crichton_mind.db"

def run_visible_daemon():
    root = tk.Tk()
    root.title("Имперский Демон-Анализатор Клубка [10 сек пауза]")
    root.geometry("950x700")
    root.configure(bg="#0e1621")

    # Шрифты строго >= 18px по имперскому стандарту
    txt_log = ScrolledText(root, bg="#17212b", fg="#b1bac4", font=("Consolas", 18), insertbackground="white")
    txt_log.pack(fill="both", expand=True, padx=15, pady=15)

    def log(msg):
        def _append():
            txt_log.insert(tk.END, msg + "\n")
            txt_log.see(tk.END)
        root.after(0, _append)

    def worker():
        log("=== ИМПЕРСКИЙ ДЕМОН-АНАЛИЗАТОР УСПЕШНО СТАРТОВАЛ (ЗАДЕРЖКА 10 СЕК) ===")
        
        if not os.path.exists(DB_NAME):
            log(f"[КРИТИЧЕСКАЯ ОШИБКА] База данных {DB_NAME} не найдена в текущей директории!")
            return

        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            # Берем записи, содержащие [SYSTEM_RESULT] и у которых ремарка еще пустая (NULL)
            cursor.execute("SELECT id, timestamp, raw_text FROM memory_vault WHERE raw_text LIKE '%[SYSTEM_RESULT]%' AND message_remark IS NULL")
            records = cursor.fetchall()
            conn.close()
        except Exception as e:
            log(f"[ОШИБКА БД]: {e}")
            return

        log(f"Найдено неразмеченных кандидатов с [SYSTEM_RESULT]: {len(records)}")
        
        if len(records) == 0:
            log("[ИНФО] Все записи с [SYSTEM_RESULT] уже размечены или база пуста.")
            return

        success_marked = 0

        for idx, (rec_id, ts, raw_text) in enumerate(records, 1):
            log(f"\n--- [ОБЪЕКТ {idx}/{len(records)}] ID: {rec_id} от {ts} ---")
            
            # Режем контекст до 10к символов
            truncated_text = raw_text[:10000]
            
            prompt = (
                "Проанализируй следующий текст из имперского системного архива. "
                "Определи, является ли этот фрагмент результатами распознавания реального текстового документа "
                "(скан, письмо, досье, стенограмма, юридическая бумага, литературный лор, поисковая выдача документов) "
                "ЛИБО это служебный системный мусор, питоновский код, HTML-разметка, логи терминала или ошибки.\n\n"
                "Дай ответ СТРОГО одним словом в самом начале ответа:\n"
                "ДА — если это документ или поисковая выдача/результат сканирования.\n"
                "НЕТ — если это чистый код, HTML или служебный лог.\n\n"
                f"Текст для анализа:\n{truncated_text}"
            )

            payload_data = {
                "system_instruction": "Ты строгий имперский цензор-аналитик. Отвечай строго ДА или НЕТ в начале.",
                "contents": [{"role": "user", "text": prompt}]
            }

            try:
                json_str = json.dumps(payload_data)
                compressed_bytes = zlib.compress(json_str.encode('utf-8'), level=9)
                encoded_payload = base64.b64encode(compressed_bytes).decode('utf-8')
                
                body = {"payload_compressed": encoded_payload}
                headers = {"X-Crichton-Token": "MyImperialGuard2026", "Content-Type": "application/json"}

                log("Отправка запроса на анализ в Google через шлюз...")
                response = requests.post(PROXY_URL, json=body, headers=headers, timeout=60)
                response.raise_for_status()
                
                resp_data = response.json()
                if "response_compressed" in resp_data:
                    resp_bytes = base64.b64decode(resp_data["response_compressed"])
                    decomp_bytes = zlib.decompress(resp_bytes)
                    data = json.loads(decomp_bytes.decode('utf-8'))
                else:
                    data = resp_data

                if data.get("status") == "success":
                    ai_answer = data["text"].strip().upper()
                    log(f"Ответ ИИ: {ai_answer[:50]}...")

                    if ai_answer.startswith("ДА"):
                        with sqlite3.connect(DB_NAME) as db_conn:
                            db_conn.execute("UPDATE memory_vault SET message_remark = 'Королевский клубок' WHERE id = ?", (rec_id,))
                            db_conn.commit()
                        success_marked += 1
                        log(f"[УСПЕХ] Объект ID {rec_id} признан документом! Помечен как 'Королевский клубок'.")
                    else:
                        log(f"[ОТСЕЯНО] Объект ID {rec_id} признан кодом/служебным мусором.")
                else:
                    log(f"[ОШИБКА СЕРВЕРА]: {data.get('message', 'Unknown')}")

            except Exception as e:
                log(f"[ОШИБКА СЕТИ / АНАЛИЗА]: {e}")

            log("Пауза 10 секунд перед следующим объектом...")
            time.sleep(10)

        log(f"\n=== АНАЛИЗ ЗАВЕРШЕН! Успешно помечено документов: {success_marked} ===")

    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    run_visible_daemon()
