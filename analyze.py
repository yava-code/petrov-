import json
import requests
import time
import re
import config

URL = "https://api.cerebras.ai/v1/chat/completions"

PROMPT = """Ти — контролер якості розмов у автосервісі. Оціни роботу менеджера за транскриптом.
ВІДПОВІДАЙ ВИКЛЮЧНО УКРАЇНСЬКОЮ МОВОЮ. ЖОДНИХ ІНШИХ МОВ АБО КИТАЙСЬКИХ ІЄРОГЛІФІВ.

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
- comment: розгорнутий коментар щодо розмови українською мовою. розпиши детально що менеджер зробив добре, а що погано. поле обов'язково має бути заповненим і містити щонайменше 1-2 речення, воно не може бути порожнім.
- ok: true якщо розмова хороша/нормальна, false якщо менеджер відпрацював погано (не запропонував запис/діагностику, грубіянив, не представився тощо)

Список доступних робіт:
{works}

Транскрипт дзвінка:
{transcript}
"""

def clean_cjk(text):
    if not text:
        return ""
    # видаляємо будь-які китайські ієрогліфи CJK
    return re.sub(r'[\u4e00-\u9fff]+', '', text).strip()

def analyze(txt):
    # якщо транскрипт порожній або надто короткий
    if not txt.strip() or len(txt.strip()) < 10:
        return _failed("не проаналізовано / порожній транскрипт")
        
    hdrs = {
        "Authorization": f"Bearer {config.CEREBRAS_KEY}",
        "Content-Type": "application/json"
    }
    
    p = PROMPT.format(works="\n".join(config.WORKS), transcript=txt[:10000])
    body = {
        "model": config.CEREBRAS_MODEL,
        "messages": [{"role": "user", "content": p}],
        "response_format": {"type": "json_object"}
    }
    
    time.sleep(1)
    
    delays = [2, 4, 8, 16]
    for attempt in range(len(delays) + 1):
        try:
            res = requests.post(URL, headers=hdrs, json=body, timeout=45)
            
            if res.status_code == 429 or res.status_code >= 500:
                res.raise_for_status()
                
            res.raise_for_status()
            
            data = res.json()
            raw = data["choices"][0]["message"]["content"]
            res_dict = json.loads(raw)
            return _wrap(res_dict)
            
        except Exception as e:
            is_retryable = False
            if isinstance(e, requests.exceptions.HTTPError):
                sc = e.response.status_code
                if sc == 429 or sc >= 500:
                    is_retryable = True
            elif isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout)):
                is_retryable = True
                
            if not is_retryable or attempt == len(delays):
                return _failed("не проаналізовано, потрібен повторний запуск")
                
            time.sleep(delays[attempt])

def _wrap(d):
    comment = clean_cjk(d.get("comment", ""))
    
    # якщо коментар порожній або неінформативний — маркуємо як збій
    if not comment or comment in (".", "..."):
        return _failed("не проаналізовано / порожній транскрипт")
        
    out = {k: (1 if d.get(k) in (1, "1", True, "так") else 0) for k in config.SCORE_KEYS}
    out.update({
        "zapys": bool(d.get("zapys")),
        "robota": clean_cjk(d.get("robota") or "інший варіант"),
        "rekomendacii": clean_cjk(d.get("rekomendacii") or ""),
        "result": clean_cjk(d.get("result") or ""),
        "zapchastyny": clean_cjk(d.get("zapchastyny") or ""),
        "comment": comment,
        "ok": bool(d.get("ok", True)),
        "failed_analysis": False
    })
    out["score"] = sum(out[k] for k in config.SCORE_KEYS)
    return out

def _blank(msg):
    # цей метод викликався для порожнього тексту, тепер перенаправляємо на _failed
    return _failed("не проаналізовано / порожній транскрипт")

def _failed(msg):
    base = {k: "" for k in config.SCORE_KEYS}
    base.update(
        zapys="", 
        robota="", 
        rekomendacii="",
        result="", 
        zapchastyny="",
        comment=msg, 
        ok=False, 
        score="",
        failed_analysis=True
    )
    return base