import os
import re
import html
import sqlite3
import numpy as np

# Прячем импорты в try-except на случай запуска вне venv
try:
    from sentence_transformers import SentenceTransformer
    import faiss
except ImportError:
    pass

DB_PATH = "crichton_mind.db"
INDEX_PATH = "crichton_vector.index"

# Глобальные переменные для ленивой загрузки (Singleton)
_model = None
_index = None
_memory_map = None

def clean_html_for_memory(raw_text):
    """
    Очищает сырой HTML-код из визуальных карточек:
    - Конвертирует блочные теги в переносы строк
    - Срезает любые <теги> и style="..."
    - Декодирует сущности (&nbsp;, &#1088; и т.д.)
    - Убирает мусорные пробелы
    """
    if not raw_text:
        return ""
    
    # 1. Сохраняем логические переносы строк на месте блочных элементов
    text = re.sub(r'<(?:br|/p|/div|/tr|/h[1-6]|/li)\s*/?>', '\n', raw_text, flags=re.IGNORECASE)
    
    # 2. Вырезаем все остальные HTML-теги вместе со стилями и атрибутами
    text = re.sub(r'<[^>]+>', '', text)
    
    # 3. Декодируем HTML-сущности
    text = html.unescape(text)
    
    # 4. Нормализуем пробелы и пустые строки
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n\n', text)
    
    return text.strip()

def _init_memory():
    global _model, _index, _memory_map
    if _model is not None:
        return
        
    print("[ПАМЯТЬ] Прогреваю векторный гиппокамп. Загрузка нейросети...")
    # --- МУЛЬТИЯЗЫЧНАЯ МАТРИЦА ---
    _model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    _index = faiss.read_index(INDEX_PATH)
    
    # Вытягиваем карту памяти точно в том же порядке, как это делал индексатор!
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, role, raw_text FROM memory_vault WHERE raw_text IS NOT NULL")
    _memory_map = cursor.fetchall()
    conn.close()
    
    print(f"[ПАМЯТЬ] Ядро готово! Векторов в индексе: {_index.ntotal}, Строк в карте: {len(_memory_map)}")

def get_memory_context(user_text, top_k=200):
    """
    Принимает текст, превращает в вектор, бьет по FAISS-индексу 
    и возвращает очищенные от HTML-тегов куски контекста.
    """
    if not os.path.exists(INDEX_PATH):
        return ""
        
    try:
        _init_memory()
        
        # Превращаем запрос в вектор
        query_vector = _model.encode([user_text], show_progress_bar=False).astype('float32')
        
        # Ищем K ближайших совпадений в гиппокампе
        distances, indices = _index.search(query_vector, top_k)
        
        context_blocks = []
        for idx in indices[0]:
            if idx != -1 and idx < len(_memory_map):
                timestamp, role, text = _memory_map[idx]
                
                # Очистка от HTML-мусора перед сборкой контекста
                clean_text = clean_html_for_memory(text)
                if clean_text:
                    context_blocks.append(f"[{timestamp}] {role}: {clean_text}")
        
        if not context_blocks:
            return ""
            
        archive = "\n\n".join(context_blocks)
        return f"--- ВСПЛЫВШИЕ ВОСПОМИНАНИЯ (ВЕКТОРНЫЙ ПОИСК) ---\n{archive}\n--------------------------------------------"
        
    except Exception as e:
        print(f"[СИСТЕМНАЯ ОШИБКА ПАМЯТИ]: {e}")
        return ""

def add_message_to_vector_index(timestamp, role, text):
    global _index, _memory_map, _model
    if not text:
        return
    try:
        _init_memory()
        if _model is None or _index is None:
            return
            
        new_vector = _model.encode([text], show_progress_bar=False).astype('float32')
        _index.add(new_vector)
        if _memory_map is None:
            _memory_map = []
        _memory_map.append((timestamp, role, text))
        faiss.write_index(_index, INDEX_PATH)
        print(f"[ПАМЯТЬ] Новый вектор добавлен. Всего векторов: {_index.ntotal}")
    except Exception as e:
        print(f"[СИСТЕМНАЯ ОШИБКА ДОБАВЛЕНИЯ ВЕКТОРА]: {e}")
