import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "silmir_dictionary.json", "r", encoding="utf-8") as f:
    _DATA = json.load(f)["entries"]

SIL_TO_RU = {}
RU_TO_SIL = {}
for item in _DATA:
    sil = item["sil"].strip()
    ru = item["ru"].strip()
    SIL_TO_RU.setdefault(sil.lower(), ru)
    # Первое совпадение считаем основным. Это сохраняет стабильность перевода.
    RU_TO_SIL.setdefault(ru.lower(), sil)

# Грамматические/служебные слова, прямо закреплённые правилами языка.
RU_TO_SIL.update({
    "я": "cəmkø",
    "ты": "pavil",
    "он": "hon",
    "она": "dat",
    "оно": "sysæg",
    "мы": "mæśærel",
    "вы": "uneź",
    "они": "ynən",
    "и": "źæś",
    "если": "vizøs",
    "не": "na",
})
SIL_TO_RU.update({v.lower(): k for k, v in RU_TO_SIL.items()})

PRONOUNS_RU = {
    "я": ("cəmkø", 1, False),
    "ты": ("pavil", 2, False),
    "он": ("hon", 3, False),
    "она": ("dat", 3, False),
    "оно": ("sysæg", 3, False),
    "мы": ("mæśærel", 1, True),
    "вы": ("uneź", 2, True),
    "они": ("ynən", 3, True),
}
PRONOUNS_SIL = {v[0].lower(): (k, v[1], v[2]) for k, v in PRONOUNS_RU.items()}

TRANSLIT_MAP = {
    "а":"a","б":"b","в":"v","г":"g","д":"d","е":"e","ё":"jo","ж":"ź","з":"z",
    "и":"i","й":"j","к":"k","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r",
    "с":"s","т":"t","у":"u","ф":"f","х":"h","ц":"c","ч":"tj","ш":"ś","щ":"śt",
    "ы":"y","э":"e","ю":"ju","я":"ja","ь":"","ъ":""
}

def transliterate_ru(word: str) -> str:
    out=[]
    for ch in word:
        low=ch.lower()
        rep=TRANSLIT_MAP.get(low, ch)
        if ch.isupper() and rep:
            rep = rep[0].upper() + rep[1:]
        out.append(rep)
    return "".join(out)

# Грубые, но полезные формы нескольких частотных русских глаголов.
# Они нужны только для распознавания входа; сам Sil'mir строится по своим правилам.
IRREGULAR_RU_VERBS = {
    "вижу":"видеть", "видишь":"видеть", "видит":"видеть", "видим":"видеть", "видите":"видеть", "видят":"видеть",
    "говорю":"говорить", "говоришь":"говорить", "говорит":"говорить", "говорим":"говорить", "говорите":"говорить", "говорят":"говорить",
    "иду":"идти", "идёшь":"идти", "идешь":"идти", "идёт":"идти", "идет":"идти", "идём":"идти", "идем":"идти", "идёте":"идти", "идете":"идти", "идут":"идти",
    "хочу":"желать", "хочешь":"желать", "хочет":"желать", "хотим":"желать", "хотите":"желать", "хотят":"желать",
    "даю":"давать", "даёшь":"давать", "даешь":"давать", "даёт":"давать", "дает":"давать", "даём":"давать", "даем":"давать", "даёте":"давать", "даете":"давать", "дают":"давать",
}

# Частотные обратные формы для красивого SIL -> RU.
RU_VERB_FORMS = {
    "видеть": {(1,False):"вижу",(2,False):"видишь",(3,False):"видит",(1,True):"видим",(2,True):"видите",(3,True):"видят"},
    "говорить": {(1,False):"говорю",(2,False):"говоришь",(3,False):"говорит",(1,True):"говорим",(2,True):"говорите",(3,True):"говорят"},
    "желать": {(1,False):"желаю",(2,False):"желаешь",(3,False):"желает",(1,True):"желаем",(2,True):"желаете",(3,True):"желают"},
    "давать": {(1,False):"даю",(2,False):"даёшь",(3,False):"даёт",(1,True):"даём",(2,True):"даёте",(3,True):"дают"},
    "идти": {(1,False):"иду",(2,False):"идёшь",(3,False):"идёт",(1,True):"идём",(2,True):"идёте",(3,True):"идут"},
}

def guess_ru_infinitive(word: str):
    w = word.lower().replace("ё", "е")
    if w in IRREGULAR_RU_VERBS:
        return IRREGULAR_RU_VERBS[w]
    # Если пользователь уже написал инфинитив.
    if w in RU_TO_SIL and (w.endswith("ть") or w.endswith("ться")):
        return w
    # Простые продуктивные модели.
    endings = [
        ("ю", ["ить","ать","ять","еть"]), ("у", ["ить","ать","ять","еть"]),
        ("ишь", ["ить"]), ("ит", ["ить"]), ("им", ["ить"]), ("ите", ["ить"]), ("ят", ["ить"]),
        ("ешь", ["ать","ять","еть"]), ("ет", ["ать","ять","еть"]), ("ем", ["ать","ять","еть"]), ("ете", ["ать","ять","еть"]), ("ют", ["ать","ять","еть"]),
    ]
    for end, infs in endings:
        if w.endswith(end) and len(w) > len(end)+1:
            stem=w[:-len(end)]
            for inf in infs:
                cand=stem+inf
                if cand in RU_TO_SIL:
                    return cand
    return None

def stats():
    return len(SIL_TO_RU), len(RU_TO_SIL)
