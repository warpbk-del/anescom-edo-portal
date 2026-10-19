import subprocess, numpy as np, glob, wave, re
SR=44100
starts=[0.8,8.5,16.3,0,0,0,0,42.4,46.3,52.3,60.3,68.3,76.4,80.3,86.3,92.3,102.3,110.3,116.6]
def load(f):
    a=subprocess.run(["ffmpeg","-v","error","-i",f,"-af","atempo=1.06","-f","f32le","-ac","1","-ar",str(SR),"-"],capture_output=True,check=True).stdout
    a=np.frombuffer(a,np.float32).astype(float)
    nz=np.where(np.abs(a)>0.008)[0]; return a[max(0,nz[0]-300):nz[-1]+3000]
out=np.zeros(125*SR); prev=0
for i,t in enumerate(starts):
    fs=sorted(glob.glob(f"dm/seg{i:02d}_*.mp3"),key=lambda x:int(re.search(r'_(\d+)\.',x).group(1)))
    parts=[]
    for f in fs: parts+= [load(f), np.zeros(int(0.2*SR))]
    a=np.concatenate(parts[:-1])
    st=max(t,prev+0.35); d=len(a)/SR
    print(f"{i:2d} target {t:5.1f} start {st:5.1f} end {st+d:5.1f}"+("  !!" if t and st-t>0.3 else ""))
    j=int(st*SR); out[j:j+len(a)]+=a[:len(out)-j]; prev=st+d
out=out/np.max(np.abs(out))*0.95
w=wave.open("vo_dm.wav","wb");w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes((out*32767).astype(np.int16).tobytes())
