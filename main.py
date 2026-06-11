import re
import shutil
from pathlib import Path
import transcribe
import analyze
import report
import config

RGX_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2})_(\d+)_")

def parse_call(fname):
    m = RGX_NAME.search(fname)
    if not m:
        return None, None
    day, _, cell = m.groups()
    return day, "38" + cell

def init_env():
    # створюємо необхідні папки
    Path(config.AUDIO_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.TRANSCRIPT_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.OUT_XLSX).parent.mkdir(parents=True, exist_ok=True)
    
    # копіюємо шаблон у правильне місце
    tpl = Path(config.TEMPLATE_XLSX)
    if not tpl.exists():
        src_tpl = Path("Звіт прослуханих розмов (1).xlsx")
        if src_tpl.exists():
            shutil.copy(src_tpl, tpl)
            
    # копіюємо тз для порядку
    tz = Path("Тз_пайтон.docx")
    if not tz.exists():
        src_tz = Path("Тз пайтон (1).docx")
        if src_tz.exists():
            shutil.copy(src_tz, tz)

def run():
    init_env()
    
    # перевіряємо чи є що аналізувати
    audio_files = list(Path(config.AUDIO_DIR).glob("*.mp3"))
    if not audio_files:
        print(f"немає mp3 файлів у папці {config.AUDIO_DIR}, закинь туди записи для роботи")
        return
        
    print("-> транскрибуємо")
    texts = transcribe.transcribe_dir(config.AUDIO_DIR, config.TRANSCRIPT_DIR)
    
    print("-> аналізуємо")
    rows = []
    for name, txt in texts.items():
        day, phone = parse_call(name)
        if not day:
            continue
        print(f"   {name}")
        rows.append({
            "date": day, "phone": phone, "file": name,
            "analysis": analyze.analyze(txt)
        })
        
    if not rows:
        print("немає коректних даних для запису")
        return
        
    print("-> записуємо звіт")
    path = report.write(rows)
    bad_calls = sum(1 for r in rows if not r["analysis"]["ok"])
    
    print(f"\nготово. файл: {path}")
    print(f"всього {len(rows)} дзвінків, проблемних — {bad_calls}")

if __name__ == "__main__":
    run()