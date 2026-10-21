import subprocess, numpy as np, glob, wave, re, json
SR=44100; DUR=48
starts=[0.6,5.0,9.0,14.0,22.4,28.4,36.2,40.0]
def load(f):
    a=subprocess.run(["ffmpeg","-v","error","-i",f,"-f","f32le","-ac","1","-ar",str(SR),"-"],capture_output=True,check=True).stdout
    a=np.frombuffer(a,np.float32).astype(float); nz=np.where(np.abs(a)>0.008)[0]; return a[max(0,nz[0]-300):nz[-1]+3000]
out=np.zeros(DUR*SR); prev=0; tl=[]
for i,t in enumerate(starts):
    fs=sorted(glob.glob(f"dm/seg{i:02d}_*.mp3"),key=lambda x:int(re.search(r'_(\d+)\.',x).group(1)))
    parts=[]
    for f in fs: parts+=[load(f),np.zeros(int(0.28*SR))]
    a=np.concatenate(parts[:-1]); st=max(t,prev+0.4); d=len(a)/SR
    tl.append([round(st,2),round(st+d,2)]); print(i,round(st,2),round(st+d,2))
    j=int(st*SR); out[j:j+len(a)]+=a[:len(out)-j]; prev=st+d
out=out/np.max(np.abs(out))*0.95
w=wave.open("vo.wav","wb");w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes((out*32767).astype(np.int16).tobytes())
json.dump(tl,open("vo_tl.json","w"))
