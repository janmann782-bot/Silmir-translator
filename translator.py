import re
from dictionary import (
    SIL_TO_RU, RU_TO_SIL, PRONOUNS_RU, PRONOUNS_SIL,
    transliterate_ru, guess_ru_infinitive, RU_VERB_FORMS
)

WORD_RE = re.compile(r"[A-Za-zÆØƏŚŹæøəśź'’]+|[А-Яа-яЁё]+|\d+|[^\w\s]", re.UNICODE)
CYR_RE = re.compile(r"[А-Яа-яЁё]")

CASE_SUFFIX = {
    "acc": "ən", "dat": "uv", "gen": "om", "ins": "yr",
    "loc": "ov", "abl": "yf", "dir": "iź", "erg": "əś",
}

PREP_CASE = {
    "в": "loc", "на": "loc", "из": "abl", "от": "abl",
    "к": "dir", "с": "ins", "со": "ins",
}

PUNCT_NO_SPACE_BEFORE = {".", ",", "!", "?", ":", ";", ")", "]", "}"}
PUNCT_NO_SPACE_AFTER = {"(", "[", "{"}

def detect_language(text: str) -> str:
    return "ru" if CYR_RE.search(text) else "sil"

def tokenize(text: str):
    return WORD_RE.findall(text)

def untokenize(tokens):
    if not tokens:
        return ""
    out=""
    for tok in tokens:
        if not out:
            out=tok
        elif tok in PUNCT_NO_SPACE_BEFORE:
            out += tok
        elif out[-1:] in PUNCT_NO_SPACE_AFTER:
            out += tok
        else:
            out += " " + tok
    return out

def _conjugate_sil(root: str, person=3, plural=False, tense="present", polite=False):
    tv = {"past":"a", "present":"i", "future":"u"}[tense]
    ending = "l" if polite else "s"
    if person == 1 and not plural:
        marker = "m"
    elif person == 2 and not plural:
        marker = "ś"
    elif person == 1 and plural:
        marker = "mn"
    elif person == 2 and plural:
        marker = "śn"
    elif person == 3 and plural:
        marker = "n"
    else:
        marker = ""
    return root + tv + marker + ending

def _parse_sil_verb(word: str):
    """Возвращает (root, tense, person, plural, polite) либо None."""
    w=word.lower()
    for polite, reg in [(False,"s"),(True,"l")]:
        if not w.endswith(reg):
            continue
        core=w[:-1]
        patterns=[
            ("mn",1,True),("śn",2,True),("n",3,True),("m",1,False),("ś",2,False),("",3,False)
        ]
        for marker,person,plural in patterns:
            if marker and not core.endswith(marker):
                continue
            base = core[:-len(marker)] if marker else core
            if not base:
                continue
            tv=base[-1:]
            if tv not in "aiu":
                continue
            root=base[:-1]
            if root.lower() in SIL_TO_RU:
                tense={"a":"past","i":"present","u":"future"}[tv]
                ru=SIL_TO_RU[root.lower()]
                if ru.endswith("ть") or ru.endswith("ться") or ru in ("желать", "давать"):
                    return root, tense, person, plural, polite, ru
    return None

def _ru_verb_person(word, subject_info):
    if subject_info:
        return subject_info[1], subject_info[2]
    w=word.lower().replace("ё","е")
    if w.endswith(("ю","у")): return 1, False
    if w.endswith(("ешь","ишь")): return 2, False
    if w.endswith(("ем","им")): return 1, True
    if w.endswith(("ете","ите")): return 2, True
    if w.endswith(("ют","ут","ят","ат")): return 3, True
    return 3, False

def _longest_ru_match(tokens, i):
    # До четырёх слов: словарь содержит много русских словосочетаний.
    for n in range(min(4,len(tokens)-i),0,-1):
        part=tokens[i:i+n]
        if any(not re.fullmatch(r"[А-Яа-яЁё]+",x) for x in part):
            continue
        phrase=" ".join(x.lower() for x in part)
        if phrase in RU_TO_SIL:
            return n, RU_TO_SIL[phrase]
    return None

def translate_ru_to_sil(text: str):
    toks=tokenize(text)
    out=[]; unknown=[]
    subject_info=None
    pending_case=None
    seen_verb=False
    i=0
    while i < len(toks):
        tok=toks[i]
        low=tok.lower()
        if not CYR_RE.search(tok):
            out.append(tok); i+=1; continue

        if low in PREP_CASE:
            pending_case=PREP_CASE[low]
            i+=1
            continue

        if low in PRONOUNS_RU:
            sil,person,plural=PRONOUNS_RU[low]
            out.append(sil)
            if subject_info is None and not seen_verb:
                subject_info=(sil,person,plural)
            i+=1; continue

        if low == "не":
            out.append("na"); i+=1; continue
        if low == "и":
            out.append("źæś"); i+=1; continue
        if low == "если":
            out.append("vizøs"); i+=1; continue

        # Сначала пробуем глагольную словоформу.
        lemma=guess_ru_infinitive(low)
        if lemma and lemma in RU_TO_SIL:
            root=RU_TO_SIL[lemma]
            person,plural=_ru_verb_person(low, subject_info)
            out.append(_conjugate_sil(root,person,plural,"present"))
            seen_verb=True
            i+=1; continue

        exact=_longest_ru_match(toks,i)
        if exact:
            n,sil=exact
            if pending_case:
                sil += CASE_SUFFIX[pending_case]
                pending_case=None
            elif seen_verb and n == 1:
                # Простая SVO-модель: первое известное существительное после глагола — объект.
                ru_gloss=" ".join(toks[i:i+n]).lower()
                if not (ru_gloss.endswith("ть") or ru_gloss.endswith("ться")):
                    sil += CASE_SUFFIX["acc"]
            out.append(sil)
            i += n
            continue

        # Неизвестное русское слово не выдумываем: просто переводим графику в алфавит Sil'mir.
        tr=transliterate_ru(tok)
        out.append(tr)
        if low not in [x.lower() for x in unknown]:
            unknown.append(tok)
        pending_case=None
        i+=1

    return untokenize(out), unknown

def _noun_decode(w: str):
    low=w.lower()
    # число + падеж. Длинные суффиксы пробуем первыми.
    case_items=sorted(CASE_SUFFIX.items(), key=lambda kv: len(kv[1]), reverse=True)
    for case,suf in case_items:
        if low.endswith(suf) and len(low)>len(suf):
            stem=low[:-len(suf)]
            plural=False; dual=False
            if stem.endswith("in") and stem[:-2] in SIL_TO_RU:
                stem=stem[:-2]; plural=True
            elif stem.endswith("et") and stem[:-2] in SIL_TO_RU:
                stem=stem[:-2]; dual=True
            if stem in SIL_TO_RU:
                gloss=SIL_TO_RU[stem]
                prep={"loc":"в ","abl":"из ","dir":"к ","ins":"с ","gen":"","dat":"","acc":"","erg":""}[case]
                # Для тестовой версии русский падеж не склоняем механически — сохраняем лемму.
                return prep + gloss
    if low.endswith("in") and low[:-2] in SIL_TO_RU:
        return SIL_TO_RU[low[:-2]] + " (мн.ч.)"
    if low.endswith("et") and low[:-2] in SIL_TO_RU:
        return SIL_TO_RU[low[:-2]] + " (два)"
    return None

def _ru_conjugate(lemma, person, plural, tense):
    if tense == "present":
        if lemma in RU_VERB_FORMS:
            return RU_VERB_FORMS[lemma].get((person,plural),lemma)
        # Нейтральный fallback: не врём о русской морфологии.
        return lemma
    if tense == "future":
        pron={1:"буду" if not plural else "будем",2:"будешь" if not plural else "будете",3:"будет" if not plural else "будут"}[person]
        return pron + " " + lemma
    return lemma + " (прош.)"

def translate_sil_to_ru(text: str):
    toks=tokenize(text)
    out=[]; unknown=[]
    for tok in toks:
        low=tok.lower()
        if not re.search(r"[A-Za-zÆØƏŚŹæøəśź]",tok):
            out.append(tok); continue
        if low == "na":
            out.append("не"); continue
        if low in SIL_TO_RU:
            out.append(SIL_TO_RU[low]); continue
        verb=_parse_sil_verb(tok)
        if verb:
            root,tense,person,plural,polite,lemma=verb
            out.append(_ru_conjugate(lemma,person,plural,tense)); continue
        noun=_noun_decode(tok)
        if noun:
            out.append(noun); continue
        out.append(tok)
        if low not in [x.lower() for x in unknown]: unknown.append(tok)
    return untokenize(out), unknown

def translate(text: str):
    if detect_language(text) == "ru":
        result, unknown = translate_ru_to_sil(text)
        return "RU → SIL", result, unknown
    result, unknown = translate_sil_to_ru(text)
    return "SIL → RU", result, unknown
