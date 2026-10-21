U=/mnt/user-data/uploads
G="crop=iw*0.62:ih*0.62:(iw-iw*0.62)/2:(ih-ih*0.62)/2,scale=1920:1080,setsar=1,fps=25,eq=saturation=0.55:contrast=1.06,colorbalance=bs=0.06:bm=0.04:rs=-0.04,format=yuv420p"
S="scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=25,eq=saturation=0.7,format=yuv420p"
while read k f t; do
 ffmpeg -nostdin -v error -y -ss $t -t 4.5 -i $U/$f.mp4 -an -vf "$G" -c:v libx264 -crf 18 -preset veryfast $k.mp4
done < /home/claude/mv/cand.txt
for t in 56 52.5 84 72 98 108 48 76 118; do ffmpeg -nostdin -v error -y -ss $t -t 4.5 -i /home/claude/vid/src.mp4 -an -vf "$S" -c:v libx264 -crf 18 -preset veryfast s$t.mp4; done
for f in *.mp4; do ffmpeg -nostdin -v error -y -ss 1.5 -i $f -frames:v 1 -vf scale=480:-1 -update 1 th_${f%.mp4}.jpg; done
python3 -c "
from PIL import Image,ImageDraw;import glob
fs=sorted(glob.glob('th_*.jpg'));W=480;H=270;c=5;r=(len(fs)+c-1)//c
im=Image.new('RGB',(W*c,H*r))
for i,f in enumerate(fs):
  a=Image.open(f);im.paste(a,((i%c)*W,(i//c)*H));ImageDraw.Draw(im).text(((i%c)*W+8,(i//c)*H+8),f[3:-4],fill='yellow')
im.save('sheet.jpg',quality=80)"
echo done
