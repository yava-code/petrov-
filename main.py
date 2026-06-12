import re
import shutil
import json
import sys
from pathlib import Path
import transcribe
import analyze
import report
import config

RGX_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2})_(\d+)_")

if "--drive" in sys.argv:
    config.DRIVE_MODE = True

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
    
    # якщо активний режим диску, спочатку завантажуємо аудіо
    if config.DRIVE_MODE:
        import drive_io
        if not Path("credentials.json").exists():
            print("помилка: файл credentials.json не знайдено в корені проєкту")
            print("будь ласка, отримайте його в Google Cloud Console та покладіть поряд з main.py")
            return
            
        print("-> скачуємо нові файли з Google Drive")
        try:
            dl_cnt = drive_io.download_audio(config.SOURCE_FOLDER_ID, config.AUDIO_DIR)
            print(f"   завантажено {dl_cnt} нових файлів")
        except Exception as e:
            print(f"помилка роботи з Google Drive: {e}")
            return
            
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
                
        if ans is None:
            ans = analyze.analyze(txt)
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
    
    # якщо активний режим диску, вивантажуємо результати назад
    if config.DRIVE_MODE:
        print("-> завантажуємо результати на Google Drive")
        try:
            import drive_io
            fid = drive_io.ensure_work_folder(config.WORK_FOLDER_NAME)
            
            # завантажуємо mp3 та розшифровки
            for r in rows:
                mp3_path = Path(config.AUDIO_DIR) / r["file"]
                txt_path = Path(config.TRANSCRIPT_DIR) / (Path(r["file"]).stem + ".txt")
                
                if mp3_path.exists():
                    drive_io.upload_or_update_file(fid, mp3_path, "audio/mpeg")
                if txt_path.exists():
                    drive_io.upload_or_update_file(fid, txt_path, "text/plain")
                    
            # завантажуємо готовий звіт
            drive_io.upload_or_update_file(
                fid, 
                config.OUT_XLSX, 
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            print("   всі результати успішно завантажено в робочу папку")
        except Exception as e:
            print(f"помилка вивантаження на Google Drive: {e}")
            
    print(f"\nготово. файл: {path}")
    print(f"всього {len(rows)} дзвінків, проблемних — {bad}, не проаналізовано — {failed}")

if __name__ == "__main__":
    run()