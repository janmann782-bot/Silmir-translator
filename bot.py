import json
import time
import html
import urllib.parse
import urllib.request
import urllib.error

from config import BOT_TOKEN
from translator import translate
from dictionary import stats

if not BOT_TOKEN or BOT_TOKEN == "ВСТАВЬ_ТОКЕН_СЮДА":
    raise SystemExit("Открой config.py и вставь BOT_TOKEN от @BotFather")

API = f"https://api.telegram.org/bot{BOT_TOKEN}/"

def api(method, data=None, timeout=70):
    body = urllib.parse.urlencode(data or {}).encode("utf-8")
    req = urllib.request.Request(API + method, data=body)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def send(chat_id, text):
    return api("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    })

def format_result(direction, translated, unknown):
    # Пользователь просил: перевод, потом два пустых абзаца, потом скрытая строка.
    result = f"<b>{html.escape(direction)}</b>\n{html.escape(translated)}"
    if unknown:
        words = ", ".join(html.escape(x) for x in unknown)
        result += f"\n\n\n\n<tg-spoiler>этих слов нет: {words}</tg-spoiler>"
    return result

def handle_message(msg):
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()
    if not text:
        return
    if text.startswith("/start") or text.startswith("/help"):
        a,b=stats()
        send(chat_id,
             "<b>Sil'mir Translator</b>\n"
             "Просто отправь текст. Кириллица считается русским, латиница Sil'mir.\n\n"
             "Если слова нет в словаре, оно остаётся как транслитерация в алфавит Sil'mir, "
             "а ниже появляется скрытый список неизвестных слов.\n\n"
             f"Словарных форм загружено: <b>{a}</b>.")
        return
    if text.startswith("/stats"):
        a,b=stats(); send(chat_id,f"Sil'mir → RU: <b>{a}</b> форм\nRU → Sil'mir: <b>{b}</b> значений")
        return
    direction, translated, unknown = translate(text)
    send(chat_id, format_result(direction, translated, unknown))

def main():
    print("Sil'mir bot запущен. Ctrl+C для остановки.")
    offset=0
    while True:
        try:
            res=api("getUpdates", {"timeout": 50, "offset": offset}, timeout=60)
            if not res.get("ok"):
                print("Telegram API error:",res); time.sleep(3); continue
            for upd in res.get("result",[]):
                offset=upd["update_id"]+1
                msg=upd.get("message") or upd.get("edited_message")
                if msg:
                    try:
                        handle_message(msg)
                    except Exception as e:
                        print("Message error:",repr(e))
                        try: send(msg["chat"]["id"], "Ошибка перевода: " + html.escape(str(e)))
                        except Exception: pass
        except KeyboardInterrupt:
            print("Остановлено."); break
        except (urllib.error.URLError, TimeoutError) as e:
            print("Сеть:",e); time.sleep(3)
        except Exception as e:
            print("Ошибка:",repr(e)); time.sleep(3)

if __name__ == "__main__":
    main()
