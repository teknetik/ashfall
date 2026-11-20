import sys, subprocess, array, math
for f in sys.argv[1:]:
    raw = subprocess.run(["ffmpeg","-v","error","-i",f,"-ac","1","-ar","44100","-f","s16le","-"],capture_output=True).stdout
    a = array.array('h', raw); win = 441*2
    def db(seg):
        m = math.sqrt(sum(x*x for x in seg)/max(1,len(seg))); return round(20*math.log10(max(m,1)/32768))
    blocks = [db(a[i:i+win]) for i in range(0, len(a), win)]
    print(f.split('/')[-1], len(a)/44100, 'start(20ms):', blocks[:15], 'end:', blocks[-15:])
