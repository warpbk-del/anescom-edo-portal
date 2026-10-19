# Оригинальный синтезированный трек для ролика: 120 BPM, ля минор, 50 тактов = 100 с.
# Структура (такт = 2 с):  0-3 интро (фильтр, без бочки) | 4-19 drop | 20 брейк | 21-29 drop
# 30 брейк | 31-45 drop | 46-49 аутро.
import numpy as np, wave, sys

SR = 44100
BPM = 120
BEAT = 60 / BPM
BAR = 4 * BEAT
NBARS = 62
N = int(NBARS * BAR * SR) + SR * 2
L = np.zeros(N); R = np.zeros(N)
rng = np.random.default_rng(7)

def note(n):  # midi -> Hz
    return 440 * 2 ** ((n - 69) / 12)

def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= len(buf): return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig * gain

def addst(start, sig, g=1.0, pan=0.0):
    add(L, start, sig, g * (1 - pan) ** 0.5 if pan > 0 else g)
    add(R, start, sig, g * (1 + pan) ** 0.5 if pan < 0 else g)

def env(n, a=0.002, d=0.1, s=0.0, rel=0.05, hold=None):
    t = np.arange(n) / SR
    e = np.ones(n)
    e[t < a] = t[t < a] / a
    m = t >= a
    e[m] = s + (1 - s) * np.exp(-(t[m] - a) / max(d, 1e-4))
    if hold is not None:
        r = t > hold
        e[r] *= np.exp(-(t[r] - hold) / rel)
    return e

def lp(x, cutoff):
    """one-pole lowpass, cutoff may be array"""
    if np.isscalar(cutoff):
        from scipy.signal import lfilter
        a = 1 - np.exp(-2 * np.pi * cutoff / SR)
        y = lfilter([a], [1, -(1 - a)], x)
        return lfilter([a], [1, -(1 - a)], y)  # 2 полюса
    c = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    a = 1 - np.exp(-2 * np.pi * c / SR)
    y = np.empty_like(x); z = 0.0
    for i in range(len(x)):
        z += a[i] * (x[i] - z); y[i] = z
    return y

def saw(f, n, detune=0.0, phase=0.0):
    t = np.arange(n) / SR
    return 2 * ((t * f * (1 + detune) + phase) % 1) - 1

# ---------- барабаны ----------
def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 48 + 120 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 6.5)
    s += 0.25 * rng.standard_normal(n) * np.exp(-t * 180)
    return np.tanh(s * 1.8)

def clap():
    n = int(0.35 * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    e = np.zeros(n)
    for k, o in enumerate([0, 0.011, 0.022, 0.034]):
        m = t >= o
        e[m] += np.exp(-(t[m] - o) * (90 if k < 3 else 14))
    s = nz * e
    s = s - lp(s, 900)  # highpass-ish
    return s * 0.8

def hat(open_=False):
    n = int((0.25 if open_ else 0.06) * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    nz = nz - lp(nz, 7000)
    return nz * np.exp(-t * (14 if open_ else 70))

K, C, HC, HO = kick(), clap(), hat(), hat(True)

# ---------- гармония ----------
# Am - F - C - G (по такту)
prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
bassn = [33, 29, 36, 31]

def bar_t(b): return b * BAR

def section(b):
    if b < 4: return 'intro'
    if b in (21, 22, 38, 39): return 'break'
    if b >= 58: return 'outro'
    return 'drop'

sc = np.ones(N)  # sidechain envelope
def duck(start):
    i = int(start * SR); n = int(0.32 * SR)
    t = np.arange(n) / SR
    e = 1 - 0.75 * np.exp(-t * 11)
    j = min(N, i + n)
    sc[i:j] = np.minimum(sc[i:j], e[: j - i])

drums_L = np.zeros(N); drums_R = np.zeros(N)
def dadd(start, sig, g, pan=0.0):
    add(drums_L, start, sig, g * (1 - max(pan, 0)))
    add(drums_R, start, sig, g * (1 + min(pan, 0)))

for b in range(NBARS):
    s = section(b); t0 = bar_t(b)
    for q in range(4):
        tb = t0 + q * BEAT
        if s in ('drop',) or (s == 'outro' and b < 60) or (s == 'intro' and b == 3 and q >= 2):
            dadd(tb, K, 0.95); duck(tb)
        if s == 'drop' and q in (1, 3):
            dadd(tb, C, 0.42)
        if s in ('drop', 'outro'):
            dadd(tb + BEAT / 2, HO, 0.16, 0.2)
            for k in range(4):
                dadd(tb + k * BEAT / 4, HC, 0.10 if k % 2 else 0.06, -0.3)
        if s == 'intro' and b >= 2:
            for k in range(2):
                dadd(tb + k * BEAT / 2, HC, 0.06, -0.3)
    # fill in last beat of every 4th drop bar
    if s == 'drop' and b % 4 == 3:
        for k in range(4):
            dadd(t0 + 3 * BEAT + k * BEAT / 4, C, 0.22)

# ---------- бас ----------
bass = np.zeros(N)
for b in range(NBARS):
    s = section(b)
    if s in ('intro', 'break') or b >= 60: continue
    f = note(bassn[b % 4])
    for k in range(8):  # оффбит-восьмые
        st = bar_t(b) + k * BEAT / 2 + BEAT / 4 * 0
        n = int(BEAT / 2 * SR * 0.9)
        x = saw(f, n) * 0.6 + np.sin(2 * np.pi * f / 2 * np.arange(n) / SR) * 0.7
        x *= env(n, 0.003, 0.12, 0.35, 0.03, hold=BEAT / 2 * 0.8)
        add(bass, st, x)
bass = lp(bass, 420)

# ---------- пэд (supersaw) ----------
pad = np.zeros(N)
for b in range(NBARS):
    n = int(BAR * SR) + int(0.3 * SR)
    chord = prog[b % 4]
    x = np.zeros(n)
    for m in chord + [chord[0] + 12]:
        for d in (-0.008, -0.003, 0.003, 0.008):
            x += saw(note(m), n, d, rng.random())
    x *= env(n, 0.08, 10, 1.0, 0.15, hold=BAR)
    add(pad, bar_t(b), x / 14)
# фильтр пэда: интро открывается, брейки открыты
cut = np.full(N, 2600.0)
tt = np.arange(N) / SR
cut[tt < 8] = 300 + 2300 * (tt[tt < 8] / 8) ** 2
h = 8 * SR
pad = np.concatenate([lp(pad[:h], cut[:h]), lp(pad[h:], 2600.0)])

# ---------- арпеджио ----------
arp = np.zeros(N)
pattern = [0, 1, 2, 3, 2, 1, 0, 2]
for b in range(NBARS):
    s = section(b)
    if b < 2 or b >= 61: continue
    chord = prog[b % 4] + [prog[b % 4][0] + 12]
    for k in range(16):
        m = chord[pattern[k % 8] % 4] + 12
        n = int(BEAT / 4 * SR)
        f = note(m)
        x = (saw(f, n) + saw(f, n, 0.006)) * 0.5
        x = x * env(n, 0.002, 0.07, 0.0)
        add(arp, bar_t(b) + k * BEAT / 4, x * (0.5 if s == 'intro' else 0.8))
arp = lp(arp, 3800)
# простое стерео-эхо для арпеджио (3/16)
dl = int(BEAT * 0.75 * SR)
arpL = arp.copy(); arpR = arp.copy()
arpR[dl:] += arp[:-dl] * 0.45
arpL[2 * dl:] += arp[:-2 * dl] * 0.25

# ---------- лид (в дропах 2 и 3) ----------
lead = np.zeros(N)
mel = [76, 74, 72, 74, 76, 79, 76, 74]  # по половинкам такта
for b in list(range(23, 38)) + list(range(40, 58)):
    for k in range(2):
        m = mel[(b * 2 + k) % 8]
        n = int(BEAT * 2 * SR * 0.95)
        f = note(m)
        t = np.arange(n) / SR
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t * 3, 0, 1)
        ph = np.cumsum(f * vib) / SR
        x = (2 * (ph % 1) - 1) * 0.5 + (2 * ((ph * 1.005) % 1) - 1) * 0.5
        x *= env(n, 0.01, 0.5, 0.55, 0.05, hold=BEAT * 1.8)
        add(lead, bar_t(b) + k * 2 * BEAT, x)
lead = lp(lead, 2400)

# ---------- райзеры и удары ----------
fx = np.zeros(N)
def riser(end, dur):
    n = int(dur * SR); t = np.arange(n) / SR
    nz = rng.standard_normal(n)
    y = lp(nz, 200 + 7000 * (t / dur) ** 2) * (t / dur) ** 1.5
    add(fx, end - dur, y * 0.5)
def impact(st):
    n = int(1.6 * SR); t = np.arange(n) / SR
    f = 55 * np.exp(-t * 1.5) + 30
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    y += lp(rng.standard_normal(n), 2500) * np.exp(-t * 4) * 0.5
    add(fx, st, y * 0.7)
for end in (8, 42, 76):
    riser(end, 2 * BAR if end == 8 else BAR)
for st in (8, 16, 46, 80, 116):
    impact(st)

# ---------- сведение ----------
mixL = drums_L * 1.0 + bass * 0.55 * sc + pad * 0.35 * sc + arpL * 0.18 * sc + lead * 0.16 * sc + fx * 0.6
mixR = drums_R * 1.0 + bass * 0.55 * sc + pad * 0.35 * sc + arpR * 0.18 * sc + lead * 0.16 * sc + fx * 0.6
# аутро: затухание последних 6 с
fade = np.ones(N)
fs, fe = 118, 124.5
m = tt > fs
fade[m] = np.clip(1 - (tt[m] - fs) / (fe - fs), 0, 1) ** 1.5
mixL *= fade; mixR *= fade
st = np.stack([mixL, mixR], 1)
st = np.tanh(st * 1.1)
st /= np.max(np.abs(st)) / 0.89
st = st[: int(125 * SR)]
out = (st * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'music.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(out.tobytes())
print('ok', len(out) / SR)
