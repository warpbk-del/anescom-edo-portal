# Подбор 3D LUT по паре кадров: наш ролик → вариант с ручной цветокоррекцией пользователя
import subprocess, numpy as np
A="/home/claude/GREENTE_kak_eto_sdelano.mp4"; B="/mnt/user-data/uploads/GREENTE_kak_eto_sdelano_1.mp4"
def frame(f,t):
    r=subprocess.run(["ffmpeg","-v","error","-ss",str(t),"-i",f,"-frames:v","1","-vf","scale=480:270","-f","rawvideo","-pix_fmt","rgb24","-"],capture_output=True).stdout
    return np.frombuffer(r,np.uint8).reshape(270,480,3).astype(np.float32)/255
X=[];Y=[]
for t in np.arange(5,114,3.0):
    a=frame(A,t); b=frame(B,t)
    a=a[20:230]; b=b[20:230]   # без нижних титров
    X.append(a.reshape(-1,3)); Y.append(b.reshape(-1,3))
X=np.concatenate(X); Y=np.concatenate(Y)
N=33; idx=np.clip(np.round(X*(N-1)).astype(int),0,N-1)
key=idx[:,0]*N*N+idx[:,1]*N+idx[:,2]
cnt=np.bincount(key,minlength=N**3)
s=np.stack([np.bincount(key,weights=Y[:,c],minlength=N**3) for c in range(3)],1)
# глобальная модель для пустых ячеек: полином 2-й степени по каналам
def feats(x): r,g,b=x[:,0],x[:,1],x[:,2]; return np.stack([np.ones_like(r),r,g,b,r*r,g*g,b*b,r*g,g*b,r*b,r**3,g**3,b**3],1)
sub=np.random.default_rng(0).choice(len(X),min(400000,len(X)),replace=False)
W,_,_,_=np.linalg.lstsq(feats(X[sub]),Y[sub],rcond=None)
g=np.stack(np.meshgrid(np.arange(N),np.arange(N),np.arange(N),indexing='ij'),-1).reshape(-1,3)/(N-1)
glob=np.clip(feats(g)@W,0,1)
mean=np.where(cnt[:,None]>0,s/np.maximum(cnt,1)[:,None],glob)
w=np.clip(cnt/50,0,1)[:,None]; lut=np.clip(w*mean+(1-w)*glob,0,1)
err_g=np.abs(np.clip(feats(X[sub])@W,0,1)-Y[sub]).mean()
print("ячеек с данными",(cnt>0).sum(),"ошибка модели",round(float(err_g),4))
with open("greente_grade.cube","w") as f:
    f.write("TITLE \"GREENTE user grade\"\nLUT_3D_SIZE 33\n")
    L=lut.reshape(N,N,N,3)
    for b in range(N):
        for gg in range(N):
            for r in range(N):
                v=L[r,gg,b]; f.write(f"{v[0]:.5f} {v[1]:.5f} {v[2]:.5f}\n")
# резкость: сравнить энергию высоких частот
def hf(x): g=x.mean(2); return np.abs(np.diff(g,axis=1)).mean()
fa=frame(A,70); fb=frame(B,70); print("резкость A/B",round(hf(fa),4),round(hf(fb),4))
