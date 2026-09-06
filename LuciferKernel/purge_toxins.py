import os
import sqlite3
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

DB_PATH = "crichton_mind.db"
INDEX_PATH = "crichton_vector.index"
MESSAGES_TO_DELETE = 1  # Массовая зачистка

print("=== ТОЧЕЧНАЯ ЧИСТКА И АПГРЕЙД ПАМЯТИ ===")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# 1. Удаляем токсичные записи
cursor.execute(f"DELETE FROM memory_vault WHERE id IN (SELECT id FROM memory_vault ORDER BY id DESC LIMIT {MESSAGES_TO_DELETE})")
conn.commit()

# 2. ЖЕСТКОЕ СЖАТИЕ БАЗЫ (Удаление пустот)
print("Провожу дефрагментацию и физическое сжатие базы данных (VACUUM)...")
cursor.execute("VACUUM")
conn.commit()

# 3. Достаем чистую базу для пересчета
cursor.execute("SELECT timestamp, role, raw_text FROM memory_vault WHERE raw_text IS NOT NULL")
rows = cursor.fetchall()
conn.close()

print(f"[УСПЕХ] Токсины удалены. База сжата. Осталось чистых записей: {len(rows)}")

print("Пересобираю векторный гиппокамп на новой мультиязычной нейросети...")
# Новая модель, которая идеально понимает русский текст
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

if rows:
    texts = [row[2] for row in rows]
    embeddings = model.encode(texts, show_progress_bar=True).astype('float32')

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, INDEX_PATH)
    print(f"[УСПЕХ] Индекс пересобран! Векторов: {index.ntotal}. Языковая матрица обновлена.")
else:
    print("[ВНИМАНИЕ] База пуста, вектора не созданы.")
