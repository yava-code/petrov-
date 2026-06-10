from pathlib import Path
from faster_whisper import WhisperModel
import config

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        # юзаємо проц і int8 щоб не мучитись з драйверами відяхи
        _engine = WhisperModel(config.WHISPER_MODEL, device="cpu", compute_type="int8")
    return _engine

def transcribe(path):
    model = get_engine()
    # мову не задаємо бо часто микс мов або суржик
    segments, _ = model.transcribe(str(path), vad_filter=True)
    return " ".join(s.text.strip() for s in segments).strip()

def transcribe_dir(src, out):
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    
    results = {}
    for f in sorted(Path(src).glob("*.mp3")):
        txt = out_path / (f.stem + ".txt")
        if txt.exists():
            results[f.name] = txt.read_text(encoding="utf-8")
            continue
            
        print(f"  обробляю {f.name}")
        text = transcribe(f)
        txt.write_text(text, encoding="utf-8")
        results[f.name] = text
        
    return results