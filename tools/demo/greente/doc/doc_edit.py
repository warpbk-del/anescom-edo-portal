# Монтаж документального ролика GREENTE «Как это сделано» (4K, 25 fps).
# Источники: цех (улучшен Video2X), станки 4K (без надписей), iPhone-сборка (только руки, фон размыт).
import subprocess, os, sys, json
W, H = (3840, 2160) if "--4k" in sys.argv else (1920, 1080)
OUT = "doc4k" if W == 3840 else "doc1080"
U = "/mnt/user-data/uploads"
SHOP = U + "/Видео_WhatsApp_2025-03-14_в_10_26_00_840f95db_realesrgan.mkv"
M = {"g20": U + "/G20.mp4", "s550": U + "/550-195.mp4", "d800": U + "/800-drill_mill.mp4",
     "s31": U + "/3_1_.mp4", "gl": U + "/glazing_bead_cutting_saw.mp4"}
IP = "/home/claude/asm/"
GR = "eq=saturation=0.6:contrast=1.05,colorbalance=bs=0.05:bm=0.03:rs=-0.04"
# (начало, конец, тип, источник, секунда в источнике, доп.параметр)
SHOTS = [
 (0.0, 4.0, "m", "s31", 151.4, None), (4.0, 7.4, "m", "s550", 129.6, None),
 (7.4, 11.0, "s", SHOP, 92.0, None), (11.0, 14.0, "s", SHOP, 40.5, None), (14.0, 17.6, "s", SHOP, 44.5, None),
 (17.6, 21.0, "s", SHOP, 4.2, None), (21.0, 24.4, "s", SHOP, 28.5, None), (24.4, 28.0, "s", SHOP, 56.0, None),
 (28.0, 31.6, "s", SHOP, 60.2, None), (31.6, 35.4, "s", SHOP, 64.2, None),
 (35.4, 39.0, "s", SHOP, 48.2, None), (39.0, 42.0, "s", SHOP, 74.0, None), (42.0, 45.6, "s", SHOP, 84.0, None),
 (45.6, 49.2, "s", SHOP, 87.8, None), (49.2, 52.6, "s", SHOP, 52.3, None), (52.6, 56.0, "s", SHOP, 68.2, None),
 (56.0, 59.6, "s", SHOP, 72.2, None),
 (59.6, 63.4, "m", "s31", 46.0, None), (63.4, 66.4, "m", "g20", 212.4, None), (66.4, 69.4, "m", "g20", 163.0, None),
 (69.4, 72.6, "m", "d800", 168.6, None), (72.6, 75.4, "m", "g20", 119.8, None), (75.4, 77.6, "m", "g20", 245.8, None),
 (77.6, 81.0, "i", "IMG_8213.MOV", 0.6, None), (81.0, 84.0, "i", "IMG_8214.MOV", 0.4, None),
 (84.0, 86.8, "i", "IMG_8222.MOV", 0.1, None), (86.8, 89.8, "m", "g20", 102.3, None),
 (89.8, 93.0, "i", "IMG_8219.MOV", 0.6, None), (93.0, 96.2, "m", "gl", 56.0, None),
 (96.2, 97.6, "i", "IMG_8213.MOV", 9.5, None),
 (97.6, 101.0, "s", SHOP, 96.2, "wrap"), (101.0, 104.2, "s", SHOP, 100.2, "wrap"), (104.2, 107.4, "s", SHOP, 105.8, None),
 (107.4, 111.4, "s", SHOP, 112.2, None), (111.4, 117.9, "s", SHOP, 104.6, "end"),
]
os.makedirs(OUT, exist_ok=True)
def run(a): subprocess.run(a, check=True)
lst = open(f"{OUT}/list.txt", "w")
for k, (a, b, typ, src, ss, extra) in enumerate(SHOTS):
    d = b - a; o = f"{OUT}/{k:02d}.mp4"
    if typ == "s":
        ss = ss + 2.0  # улучшенный файл сдвинут на ~2 с относительно исходника WhatsApp
        vf = f"scale={W}:-2:flags=lanczos,crop={W}:{H},eq=saturation=0.65:contrast=1.18:brightness=0.06:gamma=1.12,colorbalance=bs=0.04:bm=0.02:rs=-0.04,unsharp=5:5:0.4,noise=alls=3:allf=t"
        if extra == "wrap": vf += ",eq=saturation=0.55"
        if extra == "end": vf += f",gblur=sigma={28 if W==3840 else 14},eq=brightness=-0.30:saturation=0.5"
        inp = src
    elif typ == "m":
        c = 0.62
        vf = f"crop=iw*{c}:ih*{c}:(iw-iw*{c})/2:(ih-ih*{c})/2,scale={W}:{H}:flags=lanczos,{GR}"
        inp = M[src]
    else:  # iPhone: вертикаль → горизонтальная полоса с руками, фон размыт и затемнён по краям
        band = 0.5625 * 2160
        vf = (f"crop=2160:{int(band)}:0:(ih-{int(band)})/2,scale={W}:{H}:flags=lanczos,eq=saturation=0.35:contrast=1.06,"
              f"colorbalance=bs=0.06:bm=0.04,vignette=angle=PI/3.2")
        inp = IP + src
    run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", str(ss), "-t", f"{d:.3f}", "-i", inp, "-an",
         "-vf", vf + ",setsar=1,fps=25,format=yuv420p", "-c:v", "libx264", "-crf", "17", "-preset", "veryfast", o])
    lst.write(f"file '{k:02d}.mp4'\n"); print(k, typ, src if typ != "s" else "shop", ss, flush=True)
lst.close()
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c", "copy", f"{OUT}_bg.mp4"])
print("bg done")
