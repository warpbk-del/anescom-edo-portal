set -e
V=/home/claude/vid/src.mp4; S=/home/claude/gtsite/assets; O=bg
F="scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1,fps=25,format=yuv420p"
clip(){ ffmpeg -v error -y -ss $2 -t $3 -i $V -an -vf "$F,eq=saturation=1.08" -c:v libx264 -crf 18 -preset fast $O/$1.mp4; }
img(){ n=$(python3 -c "print(round($3*25))"); ffmpeg -v error -y -loop 1 -i $2 -t $3 -vf "scale=2400:1350:force_original_aspect_ratio=increase,crop=2400:1350,zoompan=z='min(zoom+0.0009,1.12)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=$n:s=1920x1080:fps=25,setsar=1,format=yuv420p" -frames:v $n -c:v libx264 -crf 18 -preset fast $O/$1.mp4; }
clip 01 72.0 4.6
clip 02 40.5 4.2
img 03 $S/factory-aluminium-cnc.jpg 5.0
clip 04 56.0 1.6
clip 05 52.5 1.6
clip 06 84.0 1.6
clip 07 98.0 1.8
clip 08 108.0 1.8
clip 09 79.0 6.0
img 10 $S/hero-glass-towers.webp 2.4
img 11 $S/tws65-assembly-turn.webp 2.4
img 12 $S/entrance-group-photoreal-v2.webp 2.6
ffmpeg -v error -y -f lavfi -i color=c=0x012f3e:s=1920x1080:r=25 -t 12.4 -pix_fmt yuv420p -c:v libx264 -crf 18 $O/13.mp4
ls $O/*.mp4 | sed "s/^/file '/;s/$/'/" | sed "s|file 'bg/|file '|" > $O/list.txt
ffmpeg -v error -y -f concat -safe 0 -i $O/list.txt -c copy bg.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 bg.mp4
