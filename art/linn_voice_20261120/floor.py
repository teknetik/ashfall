import sys, subprocess, array, math
for f in sys.argv[1:]:
    raw = subprocess.run(["ffmpeg","-v","error","-i",f,"-ac","1","-ar","44100","-f","s16le","-"],capture_output=True).stdout
    a = array.array('h', raw); win = 441*2
    peak = max(abs(x) for x in a) or 1
    bl = sorted(20*math.log10(max(math.sqrt(sum(x*x for x in a[i:i+win])/win),1)/peak) for i in range(0, len(a)-win, win))
    n=len(bl); print(f.split('/')[-1][:60].ljust(60), 'floor p5 %.0f  p15 %.0f dB re peak' % (bl[int(n*.05)], bl[int(n*.15)]))
