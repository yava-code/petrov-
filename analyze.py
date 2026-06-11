import json
import requests
import config

URL = "https://api.cerebras.ai/v1/chat/completions"

PROMPT = """Ти — контролер якості розмов у автосервісі. Оціни роботу менеджера за транскриптом.
Поверни JSON із наступними ключами:
- predstavlennia: 1 (якщо привітався і представився), інакше 0
- kuzov: 1 (якщо дізнався кузов авто/марку/модель), інакше 0
- rik: 1 (якщо запитав або дізнався рік випуску), інакше 0
- probig: 1 (якщо запитав або дізнався пробіг), інакше 0
- diagnostika: 1 (якщо запропонував діагностику), інакше 0
- mynuli_roboty: 1 (якщо дізнався про попередні ремонти), інакше 0
- zapys: true/false (чи записав на сервіс/діагностику)
- proschannia: 1 (якщо нормально попрощався), інакше 0
- robota: обрати роботу РІВНО зі списку (якщо немає підходящого — "інший варіант")
- instrukcii: 1 (чи дотримувався інструкцій/був ввічливим/активним), інакше 0
- rekomendacii: текст якщо не дотримувався інструкцій (які рекомендації порушив), інакше порожньо ""
- result: результат розмови (коротко, 1-4 слова)
- zapchastyny: чи йшлося про запчастини (коротко, або "")
- comment: коментар щодо розмови (якщо ok=false, детально розпиши що саме менеджер зробив не так/втратив клієнта/був пасивним)
- ok: true якщо розмова хороша/нормальна, false якщо менеджер відпрацював погано (не запропонував запис/діагностику, грубіянив, не представився тощо)

Список доступних робіт:
{works}

Транскрипт дзвінка:
{transcript}
"""

def analyze(txt):
    if not txt.strip():
        return _blank("порожній текст")
        
    hdrs = {
        "Authorization": f"Bearer {config.CEREBRAS_KEY}",
        "Content-Type": "application/json"
    }
    
    # лімітуємо транскрипт щоб не вийти за межі контексту
    p = PROMPT.format(works="\n".join(config.WORKS), transcript=txt[:10000])
    
    body = {
        "model": config.CEREBRAS_MODEL,
        "messages": [{"role": "user", "content": p}],
        "response_format": {"type": "json_object"}
    }
    
    try:
        # робимо запит до швидкого апі cerebras
        res = requests.post(URL, headers=hdrs, json=body, timeout=45)
        res.raise_for_status()
        data = res.json()
        raw = data["choices"][0]["message"]["content"]
        res_dict = json.loads(raw)
    except Exception as e:
        # якщо апі впало або повернуло дичину
        return _blank(f"помилка аналізу: {str(e)}")
        
    return _wrap(res_dict)

def _wrap(d):
    # пакуємо дані під колонки нашої ексельки
    out = {k: (1 if d.get(k) in (1, "1", True, "так") else 0) for k in config.SCORE_KEYS}
    out.update({
        "zapys": bool(d.get("zapys")),
        "robota": d.get("robota") or "інший варіант",
        "rekomendacii": d.get("rekomendacii") or "",
        "result": d.get("result") or "",
        "zapchastyny": d.get("zapchastyny") or "",
        "comment": d.get("comment") or "",
        "ok": bool(d.get("ok", True)),
    })
    
    # рахуємо суму балів
    out["score"] = sum(out[k] for k in config.SCORE_KEYS)
    return out

def _blank(msg):
    base = {k: 0 for k in config.SCORE_KEYS}
    base.update(
        zapys=False, 
        robota="інший варіант", 
        rekomendacii="",
        result="", 
        zapchastyny="",
        comment=msg, 
        ok=False, 
        score=0
    )
    return base