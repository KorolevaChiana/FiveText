
import os
import pytesseract
from PIL import Image

# Укажи путь к tesseract.exe, если он не прописан в системных переменных Windows
# По умолчанию пробуем стандартный путь установки Tesseract-OCR
possible_paths = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\Administrator\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
]

for p in possible_paths:
    if os.path.exists(p):
        pytesseract.pytesseract.tesseract_cmd = p
        break

IMAGES_DIR = os.path.abspath("./empire_archive/images")
OUTPUT_DIR = os.path.abspath("./empire_archive/extracted_text")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def scan_images():
    print(f"Сканирую папку с изображениями: {IMAGES_DIR}")
    if not os.path.exists(IMAGES_DIR):
        print("Папка изображений пуста.")
        return

    valid_exts = (".png", ".jpg", ".jpeg", ".bmp", ".tiff")
    files = [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(valid_exts)]
    
    if not files:
        print("Нет картинок для распознавания. Закинь файлы в empire_archive/images/")
        return

    for file in files:
        img_path = os.path.join(IMAGES_DIR, file)
        print(ж:= f"Распознаю текст на изображении: {file}...")
        try:
            img = Image.open(img_path)
            # Распознаем русский и английский языки
            text = pytesseract.image_to_string(img, lang="rus+eng")
            
            out_file = os.path.join(OUTPUT_DIR, f"{os.path.splitext(file)[0]}_ocr.txt")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[ГОТОВО] Текст сохранен в: {out_file}")
        except Exception as e:
            print(f"[ОШИБКА OCR для {file}]: {e}")

if __name__ == "__main__":
    scan_images()
