from pathlib import Path
import requests
import config

def transcribe(path):
    if not config.DEEPGRAM_KEY:
        raise ValueError("не вказано DEEPGRAM_API_KEY у .env")
        
    url = "https://api.deepgram.com/v1/listen"
    hdrs = {
        "Authorization": f"Token {config.DEEPGRAM_KEY}",
        "Content-Type": "audio/mpeg"
    }
    
    # читаємо байти файлу
    with open(path, "rb") as fh:
        audio_data = fh.read()
        
    # відправляємо в хмару deepgram
    res = requests.post(
        url, 
        headers=hdrs, 
        params=config.DEEPGRAM_PARAMS, 
        data=audio_data, 
        timeout=60
    )
    res.raise_for_status()
    data = res.json()
    
    return data["results"]["channels"][0]["alternatives"][0]["transcript"]

def transcribe_dir(src, out):
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    
    results = {}
    for f in sorted(Path(src).glob("*.mp3")):
        txt = out_path / (f.stem + ".txt")
        # перевіряємо текстовий кеш
        if txt.exists():
            results[f.name] = txt.read_text(encoding="utf-8")
            continue
            
        print(f"  транскрибую {f.name}")
        try:
            text = transcribe(f)
            txt.write_text(text, encoding="utf-8")
            results[f.name] = text
        except Exception as e:
            print(f"  помилка STT для {f.name}: {e}")
            
    return results