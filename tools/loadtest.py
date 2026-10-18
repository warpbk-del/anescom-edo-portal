"""Нагрузочный тест портала с самого сервера: python loadtest.py [одновременно=50] [запросов=500]
Бьёт по лёгким страницам (вход клиента, вход сотрудника, главная, health) — как утренний наплыв входов.
Печатает: сколько ок/ошибок, среднее и 95% время ответа, запросов в секунду."""
import sys, time, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor

N = int(sys.argv[1]) if len(sys.argv) > 1 else 50
TOTAL = int(sys.argv[2]) if len(sys.argv) > 2 else 500
BASE = "http://127.0.0.1:8096"
URLS = ["/my", "/cabinet", "/", "/health", "/my", "/help"]
res, lock = [], threading.Lock()


def hit(i):
    u = BASE + URLS[i % len(URLS)]
    t = time.time()
    try:
        with urllib.request.urlopen(u, timeout=30) as r:
            r.read()
            ok = r.status < 500
    except urllib.error.HTTPError as e:
        ok = e.code < 500
    except Exception:
        ok = False
    with lock:
        res.append((ok, time.time() - t))


t0 = time.time()
with ThreadPoolExecutor(N) as ex:
    list(ex.map(hit, range(TOTAL)))
dt = time.time() - t0
times = sorted(x[1] for x in res)
bad = sum(1 for x in res if not x[0])
print(f"одновременно {N}, запросов {TOTAL}: ошибок {bad}, среднее {sum(times) / len(times):.2f} с, "
      f"95% {times[int(len(times) * .95) - 1]:.2f} с, макс {times[-1]:.2f} с, {TOTAL / dt:.0f} запр/с")
