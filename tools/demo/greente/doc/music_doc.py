# Спокойная документальная музыка (оригинальный синтез): 76 BPM, ре минор / фа мажор,
# мягкий пэд, «пиано»-арпеджио, тихий пульс во второй половине. Длина = аргумент (сек).
import numpy as np, wave, sys
SR = 44100; DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 118.0; OUT = sys.argv[2] if len(sys.argv) > 2 else "music_doc.wav"
N = int(DUR * SR); t = np.arange(N) / SR
BPM = 76; BEAT = 60 / BPM; BAR = 4 * BEAT
rng = np.random.default_rng(7)
def note(m): return 440 * 2 ** ((m - 69) / 12)
def lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.zeros_like(x); s = 0.0
    for i in range(len(x)): s = (1 - a) * x[i] + a * s; y[i] = s
    return y
def lpf(x, fc):  # быстрый однополюсный ФНЧ через свёртку экспонентой
    a = np.exp(-2 * np.pi * fc / SR); k = int(SR * 5 / fc) + 1
    h = (1 - a) * a ** np.arange(k); return np.convolve(x, h)[: len(x)]
L = np.zeros(N); R = np.zeros(N)
def add(buf, st, sig, g=1.0):
    i = int(st * SR); j = min(N, i + len(sig))
    if i < N: buf[i:j] += sig[: j - i] * g
prog = [[62, 65, 69], [58, 62, 65], [65, 69, 72], [60, 64, 67]]  # Dm Bb F C
bass = [38, 34, 41, 36]
nb = int(DUR / BAR) + 1
# пэд
for b in range(nb):
    n = int((BAR + 1.5) * SR); x = np.zeros(n); tt = np.arange(n) / SR
    for m in prog[b % 4]:
        for d in (-0.004, 0.004):
            f = note(m - 12) * (1 + d); x += np.sin(2 * np.pi * f * tt + rng.random() * 6) + 0.3 * np.sin(4 * np.pi * f * tt)
    env = np.minimum(1, tt / 1.2) * np.minimum(1, np.maximum(0, (BAR + 1.5 - tt) / 1.5))
    x = x * env / 8
    add(L, b * BAR, x, 0.9); add(R, b * BAR, x, 0.9)
# «пиано»-арпеджио (с 2-го такта)
pat = [0, 1, 2, 1, 0, 2, 1, 2]
for b in range(1, nb):
    ch = prog[b % 4]
    for k in range(8):
        m = ch[pat[k]] + (12 if k in (2, 5) else 0)
        n = int(2.2 * SR); tt = np.arange(n) / SR; f = note(m)
        x = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(4 * np.pi * f * tt) + 0.12 * np.sin(6 * np.pi * f * tt)) * np.exp(-tt * 2.6) * np.minimum(1, tt / 0.004)
        st = b * BAR + k * BEAT / 2; pan = 0.5 + 0.35 * np.sin(k)
        add(L, st, x, 0.11 * (1.2 - pan)); add(R, st, x, 0.11 * (0.2 + pan))
# бас
for b in range(2, nb):
    n = int(BAR * SR); tt = np.arange(n) / SR; f = note(bass[b % 4])
    x = np.sin(2 * np.pi * f * tt) * np.minimum(1, tt / 0.05) * np.exp(-tt * 0.6)
    add(L, b * BAR, x, 0.22); add(R, b * BAR, x, 0.22)
# тихий пульс (вторая половина — «производство»)
for b in range(int(nb * 0.12), nb - 2):
    for k in range(8):
        n = int(0.08 * SR); x = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 60)
        x = x - lpf(x, 3000)
        add(L, b * BAR + k * BEAT / 2, x, 0.05 * (1.3 if k % 2 == 0 else 0.8)); add(R, b * BAR + k * BEAT / 2, x, 0.03)
    for k in (0, 2):
        n = int(0.4 * SR); tt = np.arange(n) / SR
        x = np.sin(2 * np.pi * (50 + 60 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9)
        add(L, b * BAR + k * BEAT, x, 0.24); add(R, b * BAR + k * BEAT, x, 0.24)
# простая реверберация: несколько задержек
def verb(x):
    y = x.copy()
    for d, g in ((0.031, 0.35), (0.047, 0.3), (0.071, 0.25), (0.113, 0.2), (0.173, 0.15)):
        k = int(d * SR); y[k:] += x[:-k] * g
    return y
L = verb(L); R = verb(R)
fade = np.minimum(1, t / 3.0) * np.minimum(1, np.maximum(0, (DUR - t) / 6.0))
st = np.stack([L * fade, R * fade], 1); st = np.tanh(st * 1.2); st /= np.max(np.abs(st)) / 0.85
w = wave.open(OUT, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st * 32767).astype(np.int16).tobytes()); w.close(); print("ok", DUR)
