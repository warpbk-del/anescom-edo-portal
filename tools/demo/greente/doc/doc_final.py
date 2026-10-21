# Финальная сборка документального ролика: титры (drawtext), логотип в начале/конце, голос + музыка.
import subprocess, sys
K = 2 if "--4k" in sys.argv else 1
BG = "doc4k_bg.mp4" if K == 2 else "doc1080_bg.mp4"
OUT = "/home/claude/GREENTE_kak_eto_sdelano_4K.mp4" if K == 2 else "/home/claude/GREENTE_kak_eto_sdelano.mp4"
FB = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
FX = "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"
LOGO = "/home/claude/deckimg/logo_light.png"
DUR = 117.9
def A(a, b, f=0.6):
    a=round(a,2); b=round(b,2)
    return (f"if(lt(t,{a}),0,if(lt(t,{round(a+f,2)}),(t-{a})/{f},if(lt(t,{round(b-f,2)}),1,if(lt(t,{b}),({b}-t)/{f},0))))")
def txt(s, font, size, x, y, a, b, color="white", extra=""):
    s = s.replace(":", "\\:").replace("'", "’")
    return (f"drawtext=fontfile={font}:text='{s}':fontsize={size*K}:fontcolor={color}:x={x}:y={y}:"
            f"alpha='{A(a, b)}'{extra}")
# этапы: (начало, конец, номер, название)
ST = [(17.9, 22.4, "01", "Химическая подготовка"), (35.7, 40.2, "02", "Порошковая покраска"),
      (52.9, 57.4, "03", "Полимеризация"), (59.9, 64.4, "04", "Резка"), (69.7, 74.2, "05", "Фрезеровка"),
      (77.9, 82.4, "06", "Сборка"), (97.9, 102.4, "07", "Упаковка")]
f = []
# вступление
f.append(txt("КАК ЭТО СДЕЛАНО", FB, 26, f"{96*K}", f"h-{300*K}", 0.6, 3.8, "0x46B254", ":borderw=0"))
f.append(txt("Алюминиевое окно", FX, 72, f"{92*K}", f"h-{250*K}", 0.9, 3.8, "white", ":shadowcolor=black@0.5:shadowx=2:shadowy=2"))
# подписи этапов (нижняя треть)
for a, b, n, name in ST:
    f.append(f"drawbox=x={80*K}:y=ih-{190*K}:w={6*K}:h={86*K}:color=0x46B254@1:t=fill:enable='between(t,{a},{b})'")
    f.append(txt(n, FX, 30, f"{104*K}", f"h-{190*K}", a, b, "0x46B254"))
    f.append(txt(name, FX, 46, f"{104*K}", f"h-{150*K}", a + 0.15, b, "white", ":shadowcolor=black@0.55:shadowx=2:shadowy=2"))
# финал
f.append(txt("От профиля до готового окна — на одном заводе", FB, 30, "(w-text_w)/2", f"h/2+{120*K}", 113.0, DUR, "0xC9DCE2"))
f.append(txt("greente.kz", FB, 26, "(w-text_w)/2", f"h/2+{175*K}", 113.6, DUR, "0x46B254"))
vf = ",".join(f)
lw = 760 * K
flt = (f"[0:v]{vf}[t];[1:v]scale={lw}:-1,format=rgba,fade=in:st=111.9:d=1.0:alpha=1[lg];"
       f"[t][lg]overlay=(W-w)/2:(H-h)/2-{60*K}:enable='gte(t,111.9)',fade=in:st=0:d=1.2,fade=out:st={DUR-1.6}:d=1.6,format=yuv420p[v];"
       f"[2:a]aformat=channel_layouts=stereo,volume=1.5,asplit[vo][sc];[3:a]volume=0.7[m];"
       f"[m][sc]sidechaincompress=threshold=0.03:ratio=5:attack=40:release=600[md];"
       f"[md][vo]amix=inputs=2:normalize=0,afade=t=out:st={DUR-2}:d=2,alimiter=limit=0.95[a]")
cmd = ["ffmpeg", "-v", "error", "-y", "-i", BG, "-loop", "1", "-t", str(DUR), "-i", LOGO, "-i", "vo_doc.wav", "-i", "music_doc.wav",
       "-filter_complex", flt, "-map", "[v]", "-map", "[a]", "-t", str(DUR), "-c:v", "libx264", "-crf", "18" if K == 2 else "19",
       "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", OUT]
subprocess.run(cmd, check=True); print("ok", OUT)
