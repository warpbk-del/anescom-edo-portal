import subprocess, os
C=os.environ.get("CLIPS","/home/claude/mv/c"); O=os.environ.get("OUT","bg2"); os.makedirs(O,exist_ok=True)
cuts=[("K",0),("P",2.4),("L",4.84),("D",7.3),("N",9.75),("G",12.4),("I",15.02),("C",17.2),("s56",19.33),("s84",22.0),("s72",24.73),("s52.5",27.9),("B",31.01),("H",33.5),("s98",36.05),("s108",38.0),("A",39.98),("E",42.5),("J",45.06),("R",47.8),("s76",50.51),("end",57.8)]
cuts=[(cuts[i][0],cuts[i][1],cuts[i+1][1]) for i in range(len(cuts)-1)]
L=open(f"{O}/list.txt","w")
for i,(k,a,b) in enumerate(cuts):
    d=b-a; sat="eq=saturation=0.45," if k.startswith("s") else ""
    o=f"{O}/{i:02d}.mp4"
    subprocess.run(["ffmpeg","-v","error","-y","-ss","0.2","-t",f"{d:.3f}","-i",f"{C}/{k}.mp4","-an","-vf",f"{sat}setpts=PTS*1.0,fps=25,format=yuv420p","-c:v","libx264","-crf",os.environ.get("CRF","18"),"-preset","fast",o],check=True)
    L.write(f"file '{i:02d}.mp4'\n")
L.close()
subprocess.run(f"ffmpeg -v error -y -f concat -safe 0 -i {O}/list.txt -c copy {O}.mp4",shell=True,check=True)
print(subprocess.run("ffprobe -v error -show_entries format=duration -of csv=p=0 "+O+".mp4",shell=True,capture_output=True,text=True).stdout)
