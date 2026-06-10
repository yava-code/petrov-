import json
import google.generativeai as genai
import config

genai.configure(api_key=config.GEMINI_KEY)

PROMPT = """Ти — контролер якості дзвінків в мережі автосервісів. Нижче транскрипт вхідного дзвінка клієнта.
Оціни роботу менеджера за чеклистом і поверни ТІЛЬКИ JSON, без markdown, без пояснень.

Чеклист (1 якщо менеджер це зробив, інакше 0):
- predstavlennia: чи представився на початку
- kuzov: чи дізнався кузов авто
- rik: чи дізнався рік авто
- probig: чи дізнався пробіг
- diagnostika: чи запропонував комплексну діагностику
- mynuli_roboty: чи дізнався які роботи робилися раніше
- proschannia: чи коректно завершив/попрощався
- instrukcii: чи дотримувався скрипту в цілому

Ще поля:
- zapys: чи записав клієнта на сервіс (true/false)
- robota: яка робота обговорювалась. ОБЕРИ РІВНО ОДНЕ значення зі списку нижче. Якщо нічого не підходить — "інший варіант".
- result: коротко результат дзвінка (1-4 слова)
- zapchastyny: чи йшлося про запчастини (коротко або "")
- comment: 1-2 речення. Якщо менеджер відповідав погано — напиши ЩО не так.
- ok: true якщо дзвінок нормальний, false якщо менеджер відпрацював погано

Список робіт:
{works}

Транскрипт:
{transcript}
"""

def analyze(text):
    if not text.strip():
        return _blank("порожній текст")
    
    prompt = PROMPT.format(works="\n".join(config.WORKS), transcript=text[:8000])
    model = genai.GenerativeModel(config.GEMINI_MODEL)
    # кидаємо запит, хочемо чистий json на виході
    res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
    
    try:
        raw = res.text.strip().strip("`").replace("json", "", 1)
        data = json.loads(raw)
    except Exception:
        return _blank("помилка парсингу відповіді")
        
    return _wrap(data)

def _wrap(d):
    # витягуємо бали та іншу інфу під формат звіту
    out = {k: (1 if d.get(k) in (1, "1", True, "так") else 0) for k in config.SCORE_KEYS}
    out.update({
        "zapys": bool(d.get("zapys")),
        "robota": d.get("robota") or "інший варіант",
        "result": d.get("result") or "",
        "zapchastyny": d.get("zapchastyny") or "",
        "comment": d.get("comment") or "",
        "ok": bool(d.get("ok", True)),
    })
    out["score"] = sum(out[k] for k in config.SCORE_KEYS)
    return out

def _blank(msg):
    base = {k: 0 for k in config.SCORE_KEYS}
    base.update(zapys=False, robota="інший варіант", result="", zapchastyny="",
                comment=msg, ok=False, score=0)
    return base