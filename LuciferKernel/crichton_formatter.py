import html

def format_text_to_html(raw_text):
    """
    Дает Крайтону полную свободу: любой HTML в тексте рендерится как есть, 
    а блоки кода (```) защищаются экранированием, чтобы код не ломал разметку.
    """
    if not raw_text:
        return ""

    # 1. Обработка блоков кода (```код```) — их экранируем обязательно
    parts = raw_text.split('`' * 3)
    html_output = ""

    for i, part in enumerate(parts):
        if i % 2 == 1:
            # Это блок кода
            lines = part.split("\n")
            if lines[0].strip() in ["python", "json", "cpp", "javascript", "cmd"]:
                code_text = "\n".join(lines[1:])
            else:
                code_text = part
            
            escaped_code = html.escape(code_text)
            html_output += f'<div class="code-block"><pre><code>{escaped_code}</code></pre></div>'
        else:
            # Обычный текст — отдаем Крайтону напрямую, разрешая любые HTML-теги
            html_output += part

    return html_output
