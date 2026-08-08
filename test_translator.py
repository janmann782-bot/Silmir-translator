from translator import translate

TESTS = [
    "Я вижу камень",
    "Я говорю язык",
    "Я люблю картошку и майонез",
    "cəmkø velims kairən",
    "cəmkø na velims kairən",
    "kairinuv",
]

for t in TESTS:
    d, out, unknown = translate(t)
    print("IN :", t)
    print("DIR:", d)
    print("OUT:", out)
    print("UNK:", unknown)
    print("-"*60)
