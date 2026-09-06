import os
import sys
import json
import threading
import io
import contextlib
import requests
import base64
import zlib
from datetime import datetime

# НОВЫЙ БОЕВОЙ ДВИЖОК
import webview
import html

# БЕЗОПАСНЫЙ ИМПОРТ РАБОТЫ С БУФЕРОМ ОБМЕНА
try:
    import pyperclip 
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False
    print("[ПРЕДУПРЕЖДЕНИЕ] Модуль pyperclip не найден! Кнопка копирования не сработает.")

# ИМПОРТ НАШЕГО МОДУЛЯ ФОРМАТИРОВАНИЯ
try:
    import crichton_formatter
    FORMATTER_AVAILABLE = True
except ImportError:
    FORMATTER_AVAILABLE = False
    print("[ПРЕДУПРЕЖДЕНИЕ] Модуль crichton_formatter.py не найден в папке!")

# БЕЗОПАСНЫЙ ИМПОРТ МОДУЛЯ ГОЛОСА (Генерал Крайтон)
try:
    import crichton_voice
    VOICE_AVAILABLE = True
except Exception as e:
    VOICE_AVAILABLE = False
    print(f"Модуль голоса недоступен: {e}")

# Принудительно включаем UTF-8 для консоли
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

SETTINGS_FILE = 'settings.json'
PROXY_URL = "http://127.0.0.1:49215/chat"

# --- СЕКРЕТНЫЙ ТОКЕН ЗАЩИТЫ ДЛЯ ШЛЮЗА ---
SECRET_TOKEN = "MyImperialGuard2026"

class TerminalApi:
    # Тонкий клиент связи между Python и веб-интерфейсом
    def __init__(self):
        self.window = None
        self.last_crichton_message = ""
        self.auto_timer = None
        self.auto_enabled = False
        self.load_settings()

    def set_window(self, window):
        self.window = window

    # --- ЗАГРУЗКА ФОНА (Жесткая инъекция) ---
    def get_base64_background(self):
        return ""

    # --- НАСТРОЙКИ ---
    def load_settings(self):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                s = json.load(f)
                self.font_size = s.get("font_size", 16)
                self.spacing = s.get("spacing", 10)
                self.power_level = s.get("power_level", 10) 
                self.memory_depth = s.get("memory_depth", 3)
        except Exception:
            self.font_size = 16
            self.spacing = 10
            self.power_level = 10
            self.memory_depth = 3

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    "font_size": self.font_size, 
                    "spacing": self.spacing,
                    "power_level": self.power_level,
                    "memory_depth": self.memory_depth
                }, f)
        except Exception: pass

    def get_initial_settings(self):
        return {
            "font_size": self.font_size, 
            "spacing": self.spacing,
            "power_level": self.power_level,
            "memory_depth": self.memory_depth
        }

    def change_setting(self, setting_type, delta):
        if setting_type == "font":
            self.font_size = max(10, min(40, self.font_size + delta))
        elif setting_type == "spacing":
            self.spacing = max(0, min(40, self.spacing + delta))
        self.save_settings()
        return {"font_size": self.font_size, "spacing": self.spacing}

    def set_power_level(self, level):
        try:
            self.power_level = int(level)
            self.save_settings()
        except: pass

    def set_memory_depth(self, level):
        try:
            self.memory_depth = int(level)
            self.save_settings()
        except: pass

    def set_autopilot(self, state):
        self.auto_enabled = state
        if not state and self.auto_timer:
            self.auto_timer.cancel()
            self.auto_timer = None

    def restart_app(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)

    def trigger_voice(self):
        if not VOICE_AVAILABLE: return
        try:
            if self.last_crichton_message:
                crichton_voice.speak_async(self.last_crichton_message)
        except Exception as e:
            print(f"Ошибка озвучки: {e}")

    # --- ЖЕЛЕЗНОЕ КОПИРОВАНИЕ ЧЕРЕЗ СЕРВЕР ---
    def python_copy_chat_from_db(self):
        if not CLIPBOARD_AVAILABLE:
            self.send_to_ui("ОШИБКА СИСТЕМЫ", "Библиотека pyperclip не установлена! Открой терминал и введи: pip3 install pyperclip", is_escaped=True)
            return
            
        try:
            payload = {"action": "get_copy_log"}
            json_str = json.dumps(payload)
            compressed = zlib.compress(json_str.encode('utf-8'), level=9)
            encoded = base64.b64encode(compressed).decode('utf-8')
            
            resp = requests.post(PROXY_URL, json={"payload_compressed": encoded}, headers={"X-Crichton-Token": SECRET_TOKEN}, timeout=20)
            data = json.loads(zlib.decompress(base64.b64decode(resp.json()["response_compressed"])).decode('utf-8'))
            
            rows = data.get("rows", [])
            if not rows:
                self.send_to_ui("Система", "База данных пуста, копировать нечего.", is_escaped=True)
                return

            chat_log = []
            for timestamp, role, text in reversed(rows):
                sender = "Королева" if role == 'user' else "Генерал Крайтон"
                time_str = timestamp if timestamp else "Неизвестно"
                chat_log.append(f"[{time_str}] {sender}:\n{text}\n")

            full_text = "\n".join(chat_log)
            pyperclip.copy(full_text)
            
            self.send_to_ui("Система", f"Успех! Последние {len(rows)} записей выгружены с сервера и скопированы в буфер.", is_escaped=True)
        except Exception as e:
            self.send_to_ui("ОШИБКА СИСТЕМЫ", f"Сбой копирования из базы: {e}", is_escaped=True)

    # --- ЗАГРУЗКА ИСТОРИИ С СЕРВЕРА ---
    def display_recent_history(self):
        try:
            payload = {"action": "get_history", "power_level": self.power_level}
            json_str = json.dumps(payload)
            compressed = zlib.compress(json_str.encode('utf-8'), level=9)
            encoded = base64.b64encode(compressed).decode('utf-8')
            
            resp = requests.post(PROXY_URL, json={"payload_compressed": encoded}, headers={"X-Crichton-Token": SECRET_TOKEN}, timeout=20)
            data = json.loads(zlib.decompress(base64.b64decode(resp.json()["response_compressed"])).decode('utf-8'))
            
            messages_to_display = data.get("history", [])
            for msg in messages_to_display:
                if "[SYSTEM_RESULT]" in msg["text"]: continue
                sender = "Королева" if msg["role"] == 'user' else "Крайтон"
                display_time = msg["timestamp"] if msg["timestamp"] else "Архив"
                if display_time and len(display_time) > 10:
                    try: display_time = datetime.strptime(display_time, "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
                    except: pass
                
                if sender in ["Королева", "Система"]:
                    safe_text = html.escape(msg["text"]).replace('\n', '<br>')
                    self.send_to_ui(sender, safe_text, display_time, is_escaped=True)
                else:
                    self.send_to_ui(sender, msg["text"], display_time)
            
            self.send_to_ui("Система", "Тонкий клиент инициализирован. Форматировщик активен.\nСвязь с транзакционным сервером установлена!", is_escaped=True)
        except Exception as e:
            self.send_to_ui("ОШИБКА СИСТЕМЫ", f"Сбой загрузки истории с сервера: {e}", is_escaped=True)

    def send_to_ui(self, sender, text, time_str=None, is_escaped=False):
        if sender == "Крайтон":
            self.last_crichton_message = text
        if not time_str:
            time_str = datetime.now().strftime("%H:%M:%S")

        if is_escaped:
            html_content = text
        else:
            if FORMATTER_AVAILABLE:
                html_content = crichton_formatter.format_text_to_html(text)
            else:
                html_content = html.escape(text).replace('\n', '<br>')

        if self.window:
            script = f"addMessage({json.dumps(sender)}, {json.dumps(html_content)}, {json.dumps(time_str)});"
            self.window.evaluate_js(script)

    def process_message(self, user_text):
        threading.Thread(target=self._process_request_thread, args=(user_text,), daemon=True).start()

    def _process_request_thread(self, user_text):
        try:
            # Тонкий клиент: отправляем на сервер только текст и настройки
            payload = {
                "action": "chat",
                "user_text": user_text,
                "power_level": self.power_level,
                "memory_depth": self.memory_depth
            }
            json_str = json.dumps(payload)
            compressed_bytes = zlib.compress(json_str.encode('utf-8'), level=9)
            encoded_payload = base64.b64encode(compressed_bytes).decode('utf-8')
            
            req_payload = {"payload_compressed": encoded_payload}
            headers = {"X-Crichton-Token": SECRET_TOKEN, "Content-Type": "application/json"} 

            response = requests.post(PROXY_URL, json=req_payload, headers=headers, timeout=120)
            response.raise_for_status()
            
            raw_response_data = response.json()
            if "response_compressed" in raw_response_data:
                resp_compressed_bytes = base64.b64decode(raw_response_data["response_compressed"])
                resp_json_bytes = zlib.decompress(resp_compressed_bytes)
                data = json.loads(resp_json_bytes.decode('utf-8'))
            else:
                data = raw_response_data

            if data.get("status") == "success":
                ai_text = data["text"]
            else:
                raise Exception(data.get("message", "Unknown error from server"))
            
            # Сервер УЖЕ записал текст в базу. Нам остается только выполнить код.
            if "[EXECUTE_PYTHON]" in ai_text and "[/EXECUTE_PYTHON]" in ai_text:
                start_idx = ai_text.find("[EXECUTE_PYTHON]") + len("[EXECUTE_PYTHON]")
                end_idx = ai_text.find("[/EXECUTE_PYTHON]")
                code_to_run = ai_text[start_idx:end_idx].strip()
                
                self.send_to_ui("Крайтон", ai_text)
                self.send_to_ui("Система", "Выполняю Python-скрипт Крайтона...", is_escaped=True)
                
                output_buffer, error_buffer = io.StringIO(), io.StringIO()
                try:
                    with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(error_buffer):
                        exec(code_to_run, {}) 
                    result = output_buffer.getvalue() or "Скрипт выполнен, вывод пуст."
                except Exception as e:
                    result = f"Ошибка выполнения: {e}\n{error_buffer.getvalue()}"
                
                sys_fb = f"[SYSTEM_RESULT]\n{result}\n[/SYSTEM_RESULT]"
                
                safe_result = html.escape(f"Результат передан на анализ:\n{result}").replace('\n', '<br>')
                self.send_to_ui("Система", safe_result, is_escaped=True)
                
                # Отправляем результат обратно на сервер (он сохранит его как запрос пользователя)
                self._process_request_thread(sys_fb)
            else:
                self.send_to_ui("Крайтон", ai_text)
                self.check_autopilot(ai_text)

        except Exception as e:
            err = str(e)
            if "ALL_KEYS_EXHAUSTED" in err: err = "[Тактическая пауза: Все ключи исчерпаны.]"
            safe_err = html.escape(err).replace('\n', '<br>')
            self.send_to_ui("ОШИБКА СИСТЕМЫ", safe_err, is_escaped=True)
        finally:
            if self.window: self.window.evaluate_js("enableInput();")

    def check_autopilot(self, ai_text):
        if self.auto_enabled:
            summary = f"Задача выполнена. {ai_text[:150]}..."
            if VOICE_AVAILABLE: crichton_voice.speak_async(summary)
            self.send_to_ui("Система", "Авто-цикл: через 1 минуту будет отправлена новая задача...", is_escaped=True)
            self.auto_timer = threading.Timer(60.0, self.trigger_auto_cmd)
            self.auto_timer.start()

    def trigger_auto_cmd(self):
        if self.auto_enabled:
            msg = "(Генерал Крайтон, определи следующую задачу и действуй !)"
            safe_msg = html.escape(msg).replace('\n', '<br>')
            self.send_to_ui("Королева", safe_msg, is_escaped=True)
            
            if self.window: self.window.evaluate_js("disableInput();")
            self.process_message(msg)

# =========================================================================================
# HTML + CSS + JS ФРОНТЕНД
# =========================================================================================
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        :root {
            --font-size: 16px;
            --spacing: 10px;
        }
        body {
            background-color: #0e1621;
            /* {{BACKGROUND_CSS}} */
            background-attachment: fixed;
            background-size: cover;
            background-position: center;
            color: #ffffff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        #sidebar {
            width: 260px;
            background-color: #17212b;
            border-right: 1px solid #000;
            display: flex;
            flex-direction: column;
            padding: 15px;
            box-sizing: border-box;
            z-index: 10;
        }
        .sidebar-title { font-size: 16px; font-weight: bold; margin-bottom: 20px; text-align: center; color: #fff; }
        .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 15px; }
        button {
            background: #2b5278; color: #fff; border: none; padding: 10px; border-radius: 6px;
            font-weight: bold; cursor: pointer; transition: 0.2s;
        }
        button:hover { background: #3b6b9a; }
        button:active { background: #1e3a54; }
        .btn-full { width: 100%; margin-bottom: 10px; }
        .btn-red { background: #8b0000; }
        .btn-red:hover { background: #b30000; }
        
        .slider-container {
            margin-bottom: 20px;
            background: rgba(0,0,0,0.2);
            padding: 10px;
            border-radius: 6px;
        }
        .slider-label {
            font-size: 14px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
        }
        .slider {
            width: 100%;
            cursor: pointer;
        }
        
        .checkbox-container { margin-bottom: 20px; display: flex; align-items: center; gap: 10px; font-size: 14px; }
        
        #main {
            flex: 1; display: flex; flex-direction: column;
            min-width: 0; 
        }
        #chat-container {
            flex: 1; 
            padding: 20px; 
            overflow-y: auto; 
            overflow-x: hidden; 
            display: flex; 
            flex-direction: column;
            min-width: 0;
        }
        
        .msg-row { 
            display: flex; 
            width: 100%; 
            margin-bottom: var(--spacing); 
            min-width: 0; 
        }
        .msg-row.Королева { justify-content: flex-end; }
        .msg-row.Крайтон { justify-content: flex-start; }
        .msg-row.Система { justify-content: center; }
        .msg-row.ОШИБКА { justify-content: center; }
        
        .bubble {
            max-width: 75%;
            padding: 10px 14px;
            border-radius: 5px; 
            font-size: var(--font-size);
            line-height: 1.45;
            position: relative;
            -webkit-user-select: text;
            user-select: text;
            min-width: 0; 
            overflow-wrap: anywhere; 
            word-wrap: break-word;
            word-break: break-word;
            overflow-x: auto; 
        }
        .bubble.Королева { background-color: rgba(43, 82, 120, 0.4); }
        .bubble.Крайтон { background-color: rgba(24, 37, 51, 0.6); }
        
        .bubble-system {
            background-color: rgba(30, 44, 58, 0.85);
            padding: 6px 14px;
            border-radius: 5px;
            font-size: calc(var(--font-size) - 2px);
            color: #7a8a96;
            text-align: center;
            -webkit-user-select: text;
            user-select: text;
            min-width: 0;
            overflow-wrap: anywhere;
            word-wrap: break-word;
            word-break: break-word;
            max-width: 90%;
        }

        .bubble table, .bubble-system table {
            max-width: 100%;
            display: block;
            overflow-x: auto;
            border-collapse: collapse;
        }

        .sender-name { color: #64b5f6; font-weight: bold; margin-bottom: 4px; font-size: calc(var(--font-size) - 1px); }
        .time { 
            font-size: calc(var(--font-size) - 4px); 
            color: rgba(255, 255, 255, 0.5); 
            float: right; margin-top: 8px; margin-left: 15px; user-select: none; 
        }
        
        .code-block {
            background-color: #0f0f0f;
            border: 1px solid #222;
            padding: 10px;
            border-radius: 5px;
            border-left: 3px solid #64b5f6;
            margin-top: 8px;
            overflow-x: auto; 
            -webkit-user-select: text;
            user-select: text;
            max-width: 100%;
            box-sizing: border-box;
        }
        pre { margin: 0; font-family: Consolas, monospace; font-size: calc(var(--font-size) - 1px); color: #a9b7c6; white-space: pre-wrap; word-break: break-word; }
        code { font-family: Consolas, monospace; }
        
        a { color: #80c7ff; text-decoration: none; }
        a:hover { text-decoration: underline; }

        b { color: #ffffff; }

        #input-container {
            background-color: #17212b; padding: 15px 20px;
            display: flex; gap: 15px; border-top: 1px solid #000;
        }
        input[type="text"] {
            flex: 1; background: #242f3d; color: #fff; border: none;
            padding: 12px 15px; border-radius: 5px; font-size: var(--font-size);
            font-family: Consolas, monospace; outline: none;
            -webkit-user-select: text;
            user-select: text;
        }
        #btn-send { width: 140px; font-size: 16px; }
        #btn-send:disabled { background: #555; cursor: not-allowed; }
    </style>
</head>
<body>
    <div id="sidebar">
        <div class="sidebar-title">ПАНЕЛЬ УПРАВЛЕНИЯ</div>
        
        <div class="slider-container">
            <div class="slider-label">
                <span>Мощность ИИ</span>
                <span id="power-val">10</span>
            </div>
            <input type="range" min="1" max="10" value="10" class="slider" id="power-slider" onchange="changePower(this.value)" oninput="updatePowerLabel(this.value)">
        </div>

        <div class="slider-container">
            <div class="slider-label">
                <span>Глубина памяти</span>
                <span id="memory-val">3</span>
            </div>
            <input type="range" min="1" max="15" value="3" class="slider" id="memory-slider" onchange="changeMemory(this.value)" oninput="updateMemoryLabel(this.value)">
        </div>

        <div class="btn-grid">
            <button onclick="changeSetting('font', -2)">A-</button>
            <button onclick="changeSetting('font', 2)">A+</button>
            <button onclick="changeSetting('spacing', -2)">↕-</button>
            <button onclick="changeSetting('spacing', 2)">↕+</button>
            <button onclick="pywebview.api.trigger_voice()" style="grid-column: span 2;">🔊 ОЗВУЧИТЬ</button>
        </div>
        
        <div class="checkbox-container">
            <input type="checkbox" id="auto-check" onchange="pywebview.api.set_autopilot(this.checked)">
            <label for="auto-check">Авто-цикл (1 мин)</label>
        </div>
        
        <button class="btn-full" onclick="copyChat()">КОПИРОВАТЬ ЧАТ</button>
        <button class="btn-full btn-red" onclick="pywebview.api.restart_app()">ПЕРЕЗАГРУЗКА ИИ</button>
    </div>

    <div id="main">
        <div id="chat-container"></div>
        <div id="input-container">
            <input type="text" id="msg-input" placeholder="Ввод команды..." onkeypress="handleEnter(event)">
            <button id="btn-send" onclick="sendMessage()">ОТПРАВИТЬ</button>
        </div>
    </div>

    <script>
        const chatBox = document.getElementById('chat-container');
        const inputField = document.getElementById('msg-input');
        const sendBtn = document.getElementById('btn-send');
        
        const powerSlider = document.getElementById('power-slider');
        const powerLabel = document.getElementById('power-val');
        
        const memorySlider = document.getElementById('memory-slider');
        const memoryLabel = document.getElementById('memory-val');

        window.addEventListener('pywebviewready', function() {
            pywebview.api.get_initial_settings().then(applySettings);
            pywebview.api.display_recent_history();
        });

        function applySettings(s) {
            document.documentElement.style.setProperty('--font-size', s.font_size + 'px');
            document.documentElement.style.setProperty('--spacing', s.spacing + 'px');
            if (s.power_level) {
                powerSlider.value = s.power_level;
                powerLabel.innerText = s.power_level;
            }
            if (s.memory_depth) {
                memorySlider.value = s.memory_depth;
                memoryLabel.innerText = s.memory_depth;
            }
        }

        function changeSetting(type, delta) {
            pywebview.api.change_setting(type, delta).then(applySettings);
        }

        function updatePowerLabel(val) { powerLabel.innerText = val; }
        function changePower(val) { pywebview.api.set_power_level(val); }

        function updateMemoryLabel(val) { memoryLabel.innerText = val; }
        function changeMemory(val) { pywebview.api.set_memory_depth(val); }

        function sendMessage() {
            const text = inputField.value.trim();
            if (!text) return;
            
            inputField.value = '';
            disableInput();
            
            const safeText = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\\n/g, '<br>');
            
            addMessage('Королева', safeText, new Date().toLocaleTimeString('ru-RU'));
            pywebview.api.process_message(text);
        }

        function handleEnter(e) {
            if (e.key === 'Enter') sendMessage();
        }

        function disableInput() {
            inputField.disabled = true;
            sendBtn.disabled = true;
            sendBtn.innerText = 'ОБРАБОТКА...';
        }

        function enableInput() {
            inputField.disabled = false;
            sendBtn.disabled = false;
            sendBtn.innerText = 'ОТПРАВИТЬ';
            inputField.focus();
        }

        function addMessage(sender, htmlContent, timeStr) {
            const row = document.createElement('div');
            
            if (sender === 'Королева') {
                row.className = 'msg-row Королева';
                row.innerHTML = `<div class="bubble Королева">${htmlContent}<div class="time">${timeStr}</div></div>`;
            } 
            else if (sender === 'Система' || sender === 'ОШИБКА СИСТЕМЫ') {
                row.className = 'msg-row Система';
                const color = sender === 'ОШИБКА СИСТЕМЫ' ? '#ff4d4d' : '#7a8a96';
                row.innerHTML = `<div class="bubble-system" style="color: ${color}"><b>${sender}</b>: ${htmlContent}</div>`;
            } 
            else {
                row.className = 'msg-row Крайтон';
                row.innerHTML = `
                    <div class="bubble Крайтон">
                        <div class="sender-name">${sender}</div>
                        ${htmlContent}
                        <div class="time">${timeStr}</div>
                    </div>`;
            }
            
            chatBox.appendChild(row);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function copyChat() {
            pywebview.api.python_copy_chat_from_db();
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    api = TerminalApi()
    
    bg_css = ""
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        fon_path = os.path.join(base_dir, "fon.jpg")
        
        if os.path.exists(fon_path):
            with open(fon_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                bg_css = f"background-image: url('data:image/jpeg;base64,{encoded}');"
    except Exception as e:
        print(f"[ОШИБКА] Сбой при инъекции фона: {e}")

    final_html = HTML_CONTENT.replace("/* {{BACKGROUND_CSS}} */", bg_css)
    
    window = webview.create_window(
        'SuperCrichton Terminal - Thin Client', 
        html=final_html,
        js_api=api,
        width=1200, 
        height=800,
        background_color='#0e1621'
    )
    api.set_window(window)
    
    webview.start()
