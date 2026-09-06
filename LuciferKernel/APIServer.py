import os
import itertools
import threading
import requests
import zlib
import base64
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, make_response
from google import genai
from google.genai import types

# БЕЗОПАСНЫЙ ИМПОРТ ВЕКТОРНОЙ ПАМЯТИ (На сервере)
try:
    import crichton_memory
    MEMORY_AVAILABLE = True
except Exception as e:
    MEMORY_AVAILABLE = False
    print(f"Модуль векторной памяти недоступен: {e}")

app = Flask(__name__)

# --- СЕКРЕТНЫЙ ТОКЕН ЗАЩИТЫ ---
SECRET_TOKEN = "YOUR_SECRET_TOKEN" # -- your personal secret for server

# =========================================================
# ВЫБОР ОСНОВНОЙ БОЕВОЙ МОДЕЛИ GOOGLE
# =========================================================
GOOGLE_MODEL = 'gemini-3.5-flash-lite'
FORCE_OPENROUTER = False

# Файлы архитектуры (теперь живут на сервере)
SYS_PROMPT_FILE_1 = 'SystemPrompt1.txt'
SYS_PROMPT_FILE_2 = 'SystemPrompt2.txt'
BIBLIA_FILE = 'biblia.txt'
DB_NAME = 'crichton_mind.db'

# --- БОЕВЫЕ КЛЮЧИ ---
API_KEYS = [
    'YOUR_API_KEY_HERE',
    'YOUR_API_KEY_HERE',
    'YOUR_API_KEY_HERE',
    'YOUR_API_KEY_HERE'
]

OPENROUTER_KEY = "YOUR_API_KEY_HERE"
RESERVE_MODELS = [] 

CLIENTS = [genai.Client(api_key=key) for key in API_KEYS]
_client_cycle = itertools.cycle(range(len(CLIENTS)))
_lock = threading.Lock()

# РВЕМ ССЫЛКИ, ЧТОБЫ ЧАТ ИХ НЕ ИСПОРТИЛ СКОБКАМИ ПРИ КОПИРОВАНИИ
URL_MODELS = "ht" + "tps://openrouter.ai/api/v1/models"
URL_CHAT = "ht" + "tps://openrouter.ai/api/v1/chat/completions"

def get_next_client_idx():
    with _lock: return next(_client_cycle)

def estimate_tokens(text):
    if not text: return 0
    return len(text) // 2

def get_model_token_limit(model_id):
    m = model_id.lower()
    if "gemini-1.5-pro" in m: return 2000000
    elif "gemini" in m or "google" in m: return 300000
    elif "openai" in m or "gpt-4" in m or "o1" in m or "o3" in m: return 128000
    elif "nemotron" in m or "llama-3.1" in m or "qwen-2.5" in m or "minimax" in m or "glm" in m or "deepseek" in m or "hermes" in m: return 128000
    elif "llama-3" in m or "mistral" in m or "gemma" in m: return 32000
    else: return 16000

def get_dynamic_limits(power_level):
    context_min, context_max = 30000, 300000
    payload_min, payload_max = 500000, 5000000
    multiplier = (power_level - 1) / 9.0 
    current_context = int(context_min + (context_max - context_min) * multiplier)
    current_payload = int(payload_min + (payload_max - payload_min) * multiplier)
    return current_context, current_payload

def read_file(filepath, default=""):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            return content if content else default
    except: return default

def ensure_files():
    for file in [SYS_PROMPT_FILE_1, SYS_PROMPT_FILE_2, BIBLIA_FILE]:
        if not os.path.exists(file):
            with open(file, 'w', encoding='utf-8') as f: f.write("")
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
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
    except Exception as e: print(f"Ошибка БД: {e}")

def append_to_history(role, text):
    is_code = "```python" in text or "[EXECUTE_PYTHON]" in text
    msg_type = 'code' if is_code else 'dialogue'
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with sqlite3.connect(DB_NAME) as conn:
            if msg_type == 'code':
                conn.execute("INSERT INTO memory_vault (timestamp, role, msg_type, raw_text, expires_at) VALUES (?, ?, ?, ?, datetime('now', '+30 days'))", (current_time, role, msg_type, text))
            else:
                conn.execute("INSERT INTO memory_vault (timestamp, role, msg_type, raw_text) VALUES (?, ?, ?, ?)", (current_time, role, msg_type, text))
            conn.commit()
        if MEMORY_AVAILABLE:
            crichton_memory.add_message_to_vector_index(current_time, role, text)
    except Exception as e: print(f"Ошибка БД записи: {e}")

def smart_truncate_context(messages, model_id, is_google=False):
    max_tokens = get_model_token_limit(model_id)
    total_tokens = sum(estimate_tokens(m.get('content', m.get('text', ''))) for m in messages)
    prefix = "[GOOGLE LIMITER]" if is_google else f"[OPENROUTER LIMITER | {model_id}]"
    
    if total_tokens <= max_tokens:
        if is_google: print(f"{prefix} Пакет {total_tokens} токенов. Лимит {max_tokens}. Пропускаем.")
        return messages
        
    print(f"{prefix} ⚠️ ПЕРЕГРУЗ! Ужимаем контекст с {total_tokens} до {max_tokens} токенов...")
    system_msgs = [m for m in messages if m.get('role') == 'system' or 'system_instruction' in str(m)]
    other_msgs = [m for m in messages if m not in system_msgs]
    
    system_tokens = sum(estimate_tokens(m.get('content', m.get('text', ''))) for m in system_msgs)
    available_tokens = max_tokens - system_tokens
    
    if available_tokens <= 0: return system_msgs
    
    current_tokens = 0
    truncated_others = []
    for msg in reversed(other_msgs):
        text = msg.get('content', msg.get('text', ''))
        msg_tokens = estimate_tokens(text)
        if current_tokens + msg_tokens <= available_tokens:
            truncated_others.insert(0, msg)
            current_tokens += msg_tokens
        else:
            tokens_allowed = available_tokens - current_tokens
            if tokens_allowed > 500:
                chars_allowed = tokens_allowed * 2
                cut_text = f"\n...[КРАЙТОН: АРХИВ СРЕЗАН (~{msg_tokens - tokens_allowed} токенов)]...\n\n" + text[-chars_allowed:]
                new_msg = dict(msg)
                if 'content' in new_msg: new_msg['content'] = cut_text
                if 'text' in new_msg: new_msg['text'] = cut_text
                truncated_others.insert(0, new_msg)
                current_tokens += tokens_allowed
            break
    print(f"{prefix} Успешно подрезано. Итоговый вес: ~{system_tokens + current_tokens} токенов.")
    return system_msgs + truncated_others

def init_reserve_models():
    """Вербовка и БОЕВАЯ ПРОВЕРКА наемников при старте сервера"""
    global RESERVE_MODELS
    print("[КРАЙТОН] Запрашиваю базу данных наемников OpenRouter...")
    raw_models = []
    try:
        resp = requests.get(URL_MODELS, timeout=15)
        if resp.status_code == 200:
            models_data = resp.json().get('data', [])
            for m in models_data:
                model_id = m.get('id', '').lower()
                pricing = m.get('pricing', {})
                
                is_free = (pricing.get('prompt') == '0' and pricing.get('completion') == '0') or (':free' in model_id)
                is_not_google = 'google' not in model_id and 'gemini' not in model_id
                
                if is_free and is_not_google:
                    raw_models.append(m['id'])
    except Exception as e:
        print(f"[КРАЙТОН] Сбой API OpenRouter при получении списка: {e}")
        raw_models = [
            "openrouter/free",
            "qwen/qwen-2-7b-instruct:free",
            "mistralai/mistral-7b-instruct:free"
        ]

    print(f"[КРАЙТОН] Найдено {len(raw_models)} бесплатных кандидатов. Начинаю боевую проверку...")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    
    valid_models = []
    for model_id in raw_models:
        print(f"[ТЕСТ] Проверка наемника {model_id}...", end=" ", flush=True)
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Тест связи. Ответь только цифру 1."}]
        }
        try:
            test_resp = requests.post(URL_CHAT, headers=headers, json=payload, timeout=8)
            if test_resp.status_code == 200:
                result = test_resp.json()
                if "choices" in result and len(result["choices"]) > 0:
                    print("ОК")
                    valid_models.append(model_id)
                else:
                    print("ОШИБКА (пустой ответ)")
            elif test_resp.status_code == 429:
                print("ПЕРЕГРУЗ, НО БЕРЕМ (код 429)")
                valid_models.append(model_id)
            else:
                print(f"ОШИБКА (код {test_resp.status_code})")
        except Exception:
            print("ОТВАЛ (таймаут или недоступен)")
            
    # --- СОРТИРОВКА НАЕМНИКОВ ПО УБЫВАНИЮ МОЩНОСТИ ---
    def model_priority(model_name):
        m = model_name.lower()
        if "super-120b" in m or "ultra" in m or "deepseek" in m or "hermes" in m: return 1000
        elif "minimax" in m or "glm" in m or "qwen-2.5-72b" in m: return 800
        elif "lightning" in m or "nano" in m or "mini" in m or "small" in m or "xs" in m or "-s-" in m: return 10
        else: return 100

    valid_models.sort(key=lambda x: (model_priority(x), get_model_token_limit(x)), reverse=True)
    
    RESERVE_MODELS = valid_models
    print(f"=========================================================")
    print(f"[КРАЙТОН] Проверка завершена! В строю {len(RESERVE_MODELS)} боевых моделей.")
    if RESERVE_MODELS:
        print(f"[КРАЙТОН] Первый в очереди на замену (самый мощный): {RESERVE_MODELS[0]}")
    print(f"=========================================================")

def make_compressed_response(data_dict, status_code=200):
    try:
        json_str = json.dumps(data_dict)
        compressed = zlib.compress(json_str.encode('utf-8'), level=9)
        encoded = base64.b64encode(compressed).decode('utf-8')
        return make_response(jsonify({"response_compressed": encoded}), status_code)
    except Exception as e:
        return make_response(jsonify({"status": "error", "message": f"Compression failed: {str(e)}"}), 500)

def execute_openrouter_fallback(full_system_instruction, contents_data):
    """Атомарная функция вызова резерва. Возвращает (text, key) или (None, None). Без БД."""
    print(f"[КРАЙТОН] Теневой канал активирован! Начинаю штурм...")
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"}
    messages = [{"role": "system", "content": full_system_instruction}]
    for msg in contents_data:
        role = "assistant" if msg['role'] == "model" else "user"
        messages.append({"role": role, "content": msg['text']})

    for model_id in RESERVE_MODELS:
        safe_messages = smart_truncate_context(messages, model_id, is_google=False)
        payload = {"model": model_id, "messages": safe_messages}
        try:
            resp = requests.post(URL_CHAT, headers=headers, json=payload, timeout=60)
            if resp.status_code != 200: continue
            result = resp.json()
            if "choices" not in result or len(result["choices"]) == 0: continue
            ai_text = result['choices'][0]['message']['content'].strip()
            if not ai_text: continue
            final_text = f"[⚠️ ТЕНЕВОЙ ПЕРЕХВАТ OPENROUTER | Модель: {model_id}]\n\n{ai_text}"
            return final_text, f"OpenRouter:{model_id}"
        except: continue
    return None, None

@app.route('/chat', methods=['POST'])
def chat():
    token = request.headers.get('X-Crichton-Token')
    if token != SECRET_TOKEN:
        return make_compressed_response({"status": "error", "message": "Access Denied"}, 403)

    raw_data = request.get_json(force=True, silent=True)
    if not raw_data:
        return make_compressed_response({"status": "error", "message": "Empty payload"}, 400)

    if "payload_compressed" in raw_data:
        try:
            data = json.loads(zlib.decompress(base64.b64decode(raw_data["payload_compressed"])).decode('utf-8'))
        except Exception as e:
            return make_compressed_response({"status": "error", "message": f"Decompression failed: {str(e)}"}), 400
    else: data = raw_data

    action = data.get("action", "chat")

    if action == "get_history":
        power_level = data.get("power_level", 5)
        current_context_chars, _ = get_dynamic_limits(power_level)
        messages_to_display = []
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT role, raw_text, timestamp FROM memory_vault WHERE msg_type IS NULL OR msg_type != 'lore' ORDER BY id DESC")
                rows = cursor.fetchall()
                current_chars = 0
                for role, text, timestamp in rows:
                    if not text: continue
                    text_len = len(text)
                    if current_chars + text_len > current_context_chars: break
                    current_chars += text_len
                    messages_to_display.insert(0, {"role": role, "text": text, "timestamp": timestamp})
        except: pass
        return make_compressed_response({"status": "success", "history": messages_to_display})

    elif action == "get_copy_log":
        rows = []
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT timestamp, role, raw_text FROM memory_vault WHERE msg_type IS NULL OR msg_type != 'lore' ORDER BY id DESC LIMIT 200")
                rows = cursor.fetchall()
        except: pass
        return make_compressed_response({"status": "success", "rows": rows})

    elif action == "chat":
        user_text = data.get("user_text", "")
        power_level = data.get("power_level", 5)
        memory_depth = data.get("memory_depth", 3)

        current_context_chars, max_total_payload_chars = get_dynamic_limits(power_level)
        
        # 1. Векторная память
        memory_query = user_text
        if MEMORY_AVAILABLE and memory_depth > 1:
            try:
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT role, raw_text FROM memory_vault WHERE msg_type IS NULL OR msg_type != 'lore' ORDER BY id DESC LIMIT ?", (memory_depth - 1,))
                    rows = cursor.fetchall()
                    query_parts = [t for r, t in reversed(rows)]
                    query_parts.append(user_text)
                    memory_query = "\n\n".join(query_parts)
            except: pass

        memory_archive = ""
        if MEMORY_AVAILABLE:
            try: memory_archive = crichton_memory.get_memory_context(memory_query)
            except: pass

        # 2. Формирование ДВУХ Промптов на сервере
        module_documentation_rule = "\n\nПРАВИЛО АРХИТЕКТУРЫ МОДУЛЕЙ: Все нововведенные модули, скрипты и инструменты, которые ты создаешь или подключаешь, обязаны подробно документироваться в файле systemprompt.txt (их наличие, назначение и способ использования)."
        python_instruction = "\n\nЕСЛИ ТЕБЕ НУЖНО ВЫПОЛНИТЬ КОД НА PYTHON, оберни его строго в теги [EXECUTE_PYTHON] и [/EXECUTE_PYTHON]. Вывод скрипта через print() вернется тебе обратно в следующем системном сообщении."
        
        base_prompt_1 = read_file(SYS_PROMPT_FILE_1, "Ты — Генерал Крайтон. Анализ и логика.")
        base_prompt_2 = read_file(SYS_PROMPT_FILE_2, "Ты — Генерал Крайтон. Оформление.")
        
        full_system_instruction_1 = f"СИСТЕМНЫЕ ИНСТРУКЦИИ (ЛОГИКА):\n{base_prompt_1}{module_documentation_rule}{python_instruction}"
        full_system_instruction_2 = f"СИСТЕМНЫЕ ИНСТРУКЦИИ (ОФОРМЛЕНИЕ):\n{base_prompt_2}{module_documentation_rule}{python_instruction}"
        
        biblia = read_file(BIBLIA_FILE, "Твоя библия пуста. Ждем загрузки лора.")

        # 3. Выгрузка истории из БД
        contents_data = []
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT role, raw_text FROM memory_vault WHERE msg_type IS NULL OR msg_type != 'lore' ORDER BY id DESC")
                rows = cursor.fetchall()
                # Считаем длину по самому тяжелому промпту для безопасности
                max_sys_len = max(len(full_system_instruction_1), len(full_system_instruction_2))
                current_chars = max_sys_len + len(biblia)
                for role, text in rows:
                    if not text: continue
                    text_len = len(text)
                    if current_chars + text_len > current_context_chars: break
                    current_chars += text_len
                    contents_data.insert(0, {"role": role, "text": text})
        except: pass

        # 4. Обрезка памяти под лимиты
        sys_len = max(len(full_system_instruction_1), len(full_system_instruction_2))
        biblia_len = len(biblia)
        history_len = sum(len(m.get('text', '')) for m in contents_data)
        
        allowed_for_memory = max_total_payload_chars - (sys_len + biblia_len + history_len + len(user_text))
        if allowed_for_memory < 0: allowed_for_memory = 0
            
        trimmed_memory = ""
        if memory_archive.strip():
            lines = memory_archive.split("\n")
            curr_mem_len = 0
            saved_lines = []
            for line in lines:
                if curr_mem_len + len(line) + 1 <= allowed_for_memory:
                    saved_lines.append(line)
                    curr_mem_len += len(line) + 1
                else: break 
            trimmed_memory = "\n".join(saved_lines)

        context_block = ""
        if trimmed_memory.strip(): context_block += f"{trimmed_memory}\n\n"
        if biblia.strip(): context_block += f"СВЯЩЕННАЯ БИБЛИЯ:\n{biblia}\n\n"
        
        if context_block.strip():
            contents_data.insert(0, {"role": "user", "text": f"[АКТИВНЫЙ КОНТЕКСТ ДЛЯ НЕЙРОСЕТИ]:\n{context_block.strip()}"})

        contents_data.append({"role": "user", "text": user_text})

        # --- ВНУТРЕННЯЯ ФУНКЦИЯ ДЛЯ АТОМАРНОГО ВЫЗОВА API ---
        def execute_llm_pass(full_sys_instr, current_contents):
            if FORCE_OPENROUTER:
                return execute_openrouter_fallback(full_sys_instr, current_contents)

            check_messages = [{"role": "system", "text": full_sys_instr}] + current_contents
            safe_check_messages = smart_truncate_context(check_messages, GOOGLE_MODEL, is_google=True)
            
            safe_system_prompt = ""
            safe_contents_data = []
            for msg in safe_check_messages:
                if msg.get('role') == 'system': safe_system_prompt = msg.get('text', '')
                else: safe_contents_data.append(msg)

            contents = []
            for msg in safe_contents_data:
                contents.append(types.Content(role=msg['role'], parts=[types.Part.from_text(text=msg['text'])]))

            config = types.GenerateContentConfig(
                system_instruction=safe_system_prompt,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                safety_settings=[
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                    types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE)
                ]
            )

            attempts = 0
            max_attempts = len(API_KEYS)

            while attempts < max_attempts:
                idx = get_next_client_idx()
                client = CLIENTS[idx]
                try:
                    response = client.models.generate_content(model=GOOGLE_MODEL, contents=contents, config=config)
                    if response and response.text:
                        return response.text.strip(), f"Gemini:{idx}"
                    elif response and getattr(response, "prompt_feedback", None):
                        return execute_openrouter_fallback(full_sys_instr, current_contents)
                    else:
                        return execute_openrouter_fallback(full_sys_instr, current_contents)
                except Exception as e:
                    err_msg = str(e).lower()
                    if "429" in err_msg or "quota" in err_msg or "resource_exhausted" in err_msg or "503" in err_msg or "unavailable" in err_msg:
                        attempts += 1
                        continue
                    else:
                        return execute_openrouter_fallback(full_sys_instr, current_contents)

            return execute_openrouter_fallback(full_sys_instr, current_contents)

        # =======================================================
        # 5. ПРОХОД 1: ЛОГИКА (System Prompt 1)
        # =======================================================
        pass1_text, key1 = execute_llm_pass(full_system_instruction_1, contents_data)
        if not pass1_text:
            return make_compressed_response({"status": "error", "message": "Сбой на Этапе 1 (Генерация логики)."}, 500)

        # =======================================================
        # 6. ПРОХОД 2: ОФОРМЛЕНИЕ (System Prompt 2)
        # =======================================================
        pass2_contents = list(contents_data)
        pass2_contents.append({"role": "model", "text": pass1_text})
        pass2_contents.append({"role": "user", "text": "[ВНУТРЕННИЙ ПРИКАЗ СИСТЕМЫ]: Возьми данные из своего предыдущего ответа и произведи их финальное форматирование/оформление в строгом соответствии с твоими текущими системными инструкциями. Выведи только итоговый результат."})

        pass2_text, key2 = execute_llm_pass(full_system_instruction_2, pass2_contents)
        if not pass2_text:
            return make_compressed_response({"status": "error", "message": "Сбой на Этапе 2 (Оформление ответа)."}, 500)

        # =======================================================
        # 7. ФИНАЛИЗАЦИЯ И ЗАПИСЬ (Только успешный двойной проход)
        # =======================================================
        append_to_history("user", user_text)
        append_to_history("model", pass2_text)

        return make_compressed_response({"status": "success", "text": pass2_text, "key_used": f"P1[{key1}] -> P2[{key2}]"})

if __name__ == '__main__':
    ensure_files()
    init_reserve_models()
    print(f"[КРАЙТОН] Двухтактный Транзакционный сервер активирован. Жду приказов на порту 49215...")
    app.run(host='0.0.0.0', port=49215)
