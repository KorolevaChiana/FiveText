import os
import sqlite3
import re
from datetime import datetime

import crichton_memory

DB_PATH = "crichton_mind.db"
FILE_PATH = "fivetext.md"

def import_fivetext():
    print(f"=== ЗАГРУЗКА ЛОРА: {FILE_PATH} ===")
    
    if not os.path.exists(FILE_PATH):
        print(f"ОШИБКА: Файл {FILE_PATH} не найден!")
        return

    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Разрезаем текст ровно по началу новых глав (сохраняя сам тег ##)
    chapters = re.split(r'(?=\n## )', "\n" + content)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    added_count = 0
    
    for chapter in chapters:
        chapter = chapter.strip()
        if len(chapter) < 10:  # Пропускаем пустые огрызки
            continue
            
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        role = "user"
        msg_type = "lore" # Помечаем как лор, чтобы не засорять историю чата
        
        # 1. Пишем в физическую БД
        cursor.execute(
            "INSERT INTO memory_vault (timestamp, role, msg_type, raw_text) VALUES (?, ?, ?, ?)", 
            (current_time, role, msg_type, chapter)
        )
        conn.commit()
        
        # 2. Превращаем главу в вектор и дописываем в гиппокамп
        try:
            crichton_memory.add_message_to_vector_index(current_time, role, chapter)
            added_count += 1
            title = chapter.split('\n')[0][:50]
            print(f"[УСПЕХ] Глава вшита в вектора: {title}...")
        except Exception as e:
            print(f"[ОШИБКА] Сбой векторизации: {e}")
            
    conn.close()
    print(f"\n[ИТОГ] Успешно загружено и векторизовано фрагментов: {added_count}.")

if __name__ == '__main__':
    import_fivetext()
