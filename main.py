import re
import transcribe, analyze, report, config

# витягуємо дату та номер з назви: 2025-09-10_15-52_0632838007_incoming.mp3
RGX_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2})_(\d+)_")

def parse_call(fname):
    match = RGX_NAME.search(fname)
    if not match:
        return None, None
    day, _, cell = match.groups()
    return day, "38" + cell # докидуємо код країни в номер

def run():
    print("-> транскрибуємо")
    texts = transcribe.transcribe_dir(config.AUDIO_DIR, config.TRANSCRIPT_DIR)

    print("-> аналізуємо")
    rows = []
    for name, txt in texts.items():
        day, phone = parse_call(name)
        print(f"   {name}")
        rows.append({
            "date": day, "phone": phone, "file": name,
            "analysis": analyze.analyze(txt)
        })

    print("-> записуємо звіт")
    path = report.write(rows)
    bad_calls = sum(1 for r in rows if not r["analysis"]["ok"])
    
    print(f"\nготово. файл: {path}")
    print(f"всього {len(rows)} дзвінків, проблемних — {bad_calls}")

if __name__ == "__main__":
    run()