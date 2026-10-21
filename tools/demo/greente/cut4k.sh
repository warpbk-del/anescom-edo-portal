U=/mnt/user-data/uploads
GR="eq=saturation=0.55:contrast=1.06,colorbalance=bs=0.06:bm=0.04:rs=-0.04"
m(){ # key file start dur cropfrac [xoff yoff]
 c=$5; x=${6:-"(iw-iw*$c)/2"}; y=${7:-"(ih-ih*$c)/2"}
 ffmpeg -nostdin -v error -y -ss $3 -t $4 -i $U/$2.mp4 -an -vf "crop=iw*$c:ih*$c:$x:$y,scale=3840:2160:flags=lanczos,setsar=1,fps=25,$GR,format=yuv420p" -c:v libx264 -crf 16 -preset fast $1.mp4; }
s(){ ffmpeg -nostdin -v error -y -ss $2 -t 4.5 -i /home/claude/vid/src.mp4 -an -vf "scale=3840:2160:force_original_aspect_ratio=increase:flags=lanczos,crop=3840:2160,unsharp=7:7:0.9,eq=saturation=0.7,setsar=1,fps=25,format=yuv420p" -c:v libx264 -crf 16 -preset fast s$2.mp4; }
m K 3_1_ 151.2 2.8 0.62
m P 550-195 129.4 4.5 0.62
m L 3_1_ 45.9 4.5 0.62
m D G20 212.2 4.5 0.62
m N G20 162.9 4.5 0.62
m G 550-195 121.7 3.2 0.5 iw*0.45 ih*0.42
m I 800-drill_mill 168.5 4.5 0.62
m C G20 119.6 4.5 0.62
m B G20 102.1 4.5 0.62
m H 550-195 160.6 4.5 0.62
m A G20 88.7 4.5 0.62
m E G20 245.7 4.5 0.62
m J glazing_bead_cutting_saw 55.8 3.2 0.62
m R 3_1_ 80.0 4.5 0.62
for t in 56 84 72 52.5 98 108 76; do s $t; done
echo cut-done
