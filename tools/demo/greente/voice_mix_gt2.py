import subprocess, numpy as np, glob, wave, re, json
SR=44100
def load(f):
    a=subprocess.run(["ffmpeg","-v","error","-i",f,"-f","f32le","-ac","1","-ar",str(SR),"-"],capture_output=True,check=True).stdout
    a=np.frombuffer(a,np.float32).astype(float); nz=np.where(np.abs(a)>0.008)[0]; return a[max(0,nz[0]-300):nz[-1]+3000]
segs=[]
for i in range(11):
    fs=sorted(glob.glob(f"dm2/seg{i:02d}_*.mp3"),key=lambda x:int(re.search(r'_(\d+)\.',x).group(1)))
    parts=[]
    for f in fs: parts+=[load(f),np.zeros(int(0.25*SR))]
    segs.append(np.concatenate(parts[:-1]))
gaps=[0.9]+[0.7]*9+[1.2]  # pause before each phrase
t=0.6; tl=[]
for i,a in enumerate(segs):
    t+=gaps[i] if i else 0; d=len(a)/SR; tl.append([round(t,2),round(t+d,2)]); t+=d
DUR=round(t+4.5,1); out=np.zeros(int(DUR*SR))
for (s,e),a in zip(tl,segs): j=int(s*SR); out[j:j+len(a)]+=a
out=out/np.max(np.abs(out))*0.95
w=wave.open("vo2.wav","wb");w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes((out*32767).astype(np.int16).tobytes())
json.dump({"dur":DUR,"tl":tl},open("vo2_tl.json","w")); print(DUR, tl)
