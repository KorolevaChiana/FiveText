import os
import re
import sqlite3
from datetime import datetime

INBOX_DIR = "inbox"
DB_NAME = "crichton_mind.db"

def import_dialogues_pure_sql():
    if not os.path.exists(INBOX_DIR):
        print(f"[ОШИБКА] Папка {INBOX_DIR} не найдена.")
        return

    files = [f for f in os.listdir(INBOX_DIR) if f.endswith('.txt')]
    if not files:
        print(f"[ОШИБКА] В папке {INBOX_DIR} нет текстовых файлов.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS memory_vault ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, "
        "role TEXT NOT NULL, "
        "msg_type TEXT DEFAULT 'dialogue', "
        "raw_text TEXT, "
        "summary TEXT, "
        "importance INTEGER DEFAULT 3, "
        "expires_at DATETIME, "
        "vector_id TEXT)"
    )

    user_markers = re.compile(r'^(Вы сказали:|пользователь сказал:)', re.IGNORECASE)
    model_markers = re.compile(r'^(Simbiot сказал:|ChatGPT сказал:)', re.IGNORECASE)

    total_inserted = 0

    for filename in files:
        filepath = os.path.join(INBOX_DIR, filename)
        print(раскручиваю := f"Читаю файл: {filename}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        current_role = None
        current_buffer = []

        def save_block():
            nonlocal total_inserted
            if not current_role or not current_buffer:
                return
            
            text = "".join(current_buffer).strip()
            text = re.sub(r'^(думал на протяжении|thought for).*?\n', '', text, flags=re.IGNORECASE).strip()
            
            if text:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO memory_vault (timestamp, role, msg_type, raw_text) VALUES (?, ?, 'dialogue', ?)",
                    (timestamp, current_role, text)
                )
                total_inserted += 1

        for line in lines:
            stripped = line.strip()

            if user_markers.match(stripped):
                save_block()
                current_role = 'user'
                current_buffer = []
                continue
            
            if model_markers.match(stripped):
                save_block()
                current_role = 'model'
                current_buffer = []
                continue

            if current_role:
                current_buffer.append(line)

        save_block()

    conn.commit()
    conn.close()
    print(f"Готово. Чистых реплик записано в базу: {total_inserted}")

if __name__ == "__main__":
    import_dialogues_pure_sql()
