import os
import sys
import subprocess
import asyncio

def ensure_dependencies():
    try:
        import playwright
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

async def interactive_google_search():
    ensure_dependencies()
    from playwright.async_api import async_playwright
    
    user_data_dir = os.path.abspath("./chrome_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    print(f"[ИНТЕРАКТИВ] Запуск постоянного профиля Chrome: {user_data_dir}")
    
    async with async_playwright() as p:
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False, # Видимый режим для человека
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            viewport={"width": 1280, "height": 800}
        )
        
        page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
        
        # Открываем Google на чистом английском/русском (без эстонского)
        target_url = "https://www.google.com/?hl=ru"
        print(f"[ПЕРЕХОД] Открываем: {target_url}")
        await page.goto(target_url, timeout=60000)
        
        print("
" + "="*50)
        print("БРАУЗЕР ОТКРЫТ И ЖДЕТ ВАС!")
        print("1. Авторизуйтесь в Google (если нужно).")
        print("2. Примите куки или пройдите капчу.")
        print("3. Введите нужный поисковый запрос прямо в окне браузера.")
        print("Когда закончите работу в браузере, вернитесь сюда и нажмите ENTER в консоли для сохранения результатов.")
        print("="*50 + "
")
        
        # Ждем подтверждения от пользователя в консоли
        input("Нажмите ENTER в этом окне после завершения всех действий в браузере...")
        
        # Сохраняем финальное состояние
        output_html = "interactive_search_result.html"
        output_screenshot = "interactive_search_screenshot.png"
        
        html_content = await page.content()
        with open(output_html, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        await page.screenshot(path=output_screenshot, full_page=True)
        text_content = await page.evaluate("document.body.innerText")
        
        print(f"[УСПЕХ] Данные сохранены! Длина текста: {len(text_content)} символов.")
        
        # Закрываем браузер
        await browser_context.close()
        return text_content

if __name__ == "__main__":
    asyncio.run(interactive_google_search())
