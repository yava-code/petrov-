import re
import shutil
import json
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
    Path(config.AUDIO_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.TRANSCRIPT_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.OUT_XLSX).parent.mkdir(parents=True, exist_ok=True)
    
    tpl = Path(config.TEMPLATE_XLSX)
    if not tpl.exists():
        src_tpl = Path("Звіт прослуханих розмов (1).xlsx")
        if src_tpl.exists():
            shutil.copy(src_tpl, tpl)
            
    tz = Path("Тз_пайтон.docx")
    if not tz.exists():
        src_tz = Path("Тз пайтон (1).docx")
        if src_tz.exists():
            shutil.copy(src_tz, tz)

def run():
    init_env()
    
    audio_files = list(Path(config.AUDIO_DIR).glob("*.mp3"))
    if not audio_files:
        print(f"немає mp3 файлів у папці {config.AUDIO_DIR}, закинь записи")
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
        
        # перевіряємо чи є вже готовий успішний аналіз
        json_path = Path(config.TRANSCRIPT_DIR) / (Path(name).stem + ".json")
        ans = None
        
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as fh:
                    cached = json.load(fh)
                if not cached.get("failed_analysis"):
                    ans = cached
                    print("     (взято з кешу)")
            except Exception:
                pass
                
        # якщо кешу немає або була помилка, робимо новий запит
        if ans is None:
            ans = analyze.analyze(txt)
            # кешуємо тільки успішні розбори
            if not ans.get("failed_analysis"):
                try:
                    with open(json_path, "w", encoding="utf-8") as fh:
                        json.dump(ans, fh, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                    
        rows.append({
            "date": day, "phone": phone, "file": name,
            "analysis": ans
        })
        
    if not rows:
        print("немає коректних даних")
        return
        
    print("-> записуємо звіт")
    path = report.write(rows)
    bad = sum(1 for r in rows if not r["analysis"].get("failed_analysis") and not r["analysis"].get("ok"))
    failed = sum(1 for r in rows if r["analysis"].get("failed_analysis"))
    
    print(f"\nготово. файл: {path}")
    print(f"всього {len(rows)} дзвінків, проблемних — {bad}, не проаналізовано — {failed}")

if __name__ == "__main__":
    run()