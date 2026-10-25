# 21-П: развернуть выгрузку .dt в новую файловую базу (фоном). Параметры: DT_MASK (маска файла в D:\Base\1C), IB_DIR (каталог новой базы).
# Пароль не нужен (новая пустая база). Журнал: <IB_DIR>_restore.log. Проверка: DEPLOY_CHECK=True — показать хвост журнала и процесс.
import glob, os, subprocess
DT_MASK = globals().get("DT_MASK", r"D:\Base\1C\prod_KA_backup_2026_10_25*")
IB_DIR = globals().get("IB_DIR", r"D:\Base\1C\AVTOKOMP_FIX")
LOGF = IB_DIR + "_restore.log"
exe = sorted(glob.glob(r"C:\Program Files\1cv8\8.3.25*\bin\1cv8.exe") + glob.glob(r"C:\Program Files\1cv8\8.3.2*\bin\1cv8.exe"))
print("платформа:", exe[-1] if exe else "НЕ НАЙДЕНА")
if globals().get("DEPLOY_CHECK"):
    for f in (LOGF, IB_DIR + "_create.log"):
        if os.path.exists(f): print(f, "→", open(f, encoding="utf-8-sig", errors="replace").read()[-600:])
    if os.path.exists(IB_DIR + r"\1Cv8.1CD"): print("1Cv8.1CD:", round(os.path.getsize(IB_DIR + r"\1Cv8.1CD") / 1e9, 2), "ГБ")
    print(os.popen('tasklist /FI "IMAGENAME eq 1cv8.exe"').read()[-400:])
else:
    dt = [f for f in glob.glob(DT_MASK) if os.path.isfile(f)]
    print("выгрузка:", dt, [round(os.path.getsize(f) / 1e9, 2) for f in dt])
    assert len(dt) == 1 and exe, "нет файла .dt или платформы"
    assert not os.path.exists(IB_DIR + r"\1Cv8.1CD"), "база уже существует — не перезаписываю"
    bat = IB_DIR + "_deploy.bat"
    open(bat, "w", encoding="cp866").write(
        f'"{exe[-1]}" CREATEINFOBASE File="{IB_DIR}" /Out "{IB_DIR}_create.log"\r\n'
        f'"{exe[-1]}" DESIGNER /F "{IB_DIR}" /DisableStartupDialogs /DisableStartupMessages /RestoreIB "{dt[0]}" /Out "{LOGF}"\r\n'
        f'echo ГОТОВО >> "{LOGF}"\r\n')
    p = subprocess.Popen(["cmd", "/c", bat], creationflags=0x00000008 | 0x00000200)
    print("запущено фоном, PID", p.pid, "| журнал", LOGF)
print("ГОТОВО deployDT")
