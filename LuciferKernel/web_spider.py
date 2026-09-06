import os
import sys
import subprocess

def ensure_dependencies():
    try:
        import playwright
    except ImportError:
        print("Установка движка Playwright...")
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

async def fetch_web_page(url, output_html="scraped_page.html", output_screenshot="scraped_screenshot.png"):
    ensure_dependencies()
    from playwright.async_api import async_playwright
    
    user_data_dir = os.path.abspath("./chrome_profile")
    os.makedirs(user_data_dir, exist_ok=True)
    
    print(f"[ВЕБ-КРАУЛЕР] Запуск браузера с постоянным профилем: {user_data_dir}")
    
    async with async_playwright() as p:
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            viewport={"width": 1280, "height": 800}
        )
        
        page = browser_context.pages[0] if browser_context.pages else await browser_context.new_page()
        
        try:
            print(f"[ПЕРЕХОД] Открываем: {url}")
            await page.goto(url, timeout=60000, wait_until="networkidle")
            
            await page.wait_for_timeout(3000)
            
            html_content = await page.content()
            with open(output_html, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"[УСПЕХ] HTML сохранен в {output_html}")
            
            await page.screenshot(path=output_screenshot, full_page=True)
            print(f"[СКРИНШОТ] Сохранен в {output_screenshot}")
            
            text_content = await page.evaluate("document.body.innerText")
            
            await browser_context.close()
            return text_content
            
        except Exception as e:
            print(f"[ОШИБКА КРАУЛЕРА] {e}")
            await browser_context.close()
            return None
