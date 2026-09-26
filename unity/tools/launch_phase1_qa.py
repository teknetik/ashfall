"""Launch an isolated native 1080p QA player; preserves the user's preferences."""
import argparse,base64,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('evidence',type=Path)
parser.add_argument('--capped',action='store_true',help='Use VSync and a 60 FPS limit.')
parser.add_argument('--background',action='store_true',help='Opt in to development-only background static capture.')
parser.add_argument('--display',default=os.environ.get('DISPLAY'),help='X11 display for the native window (defaults to DISPLAY).')
args=parser.parse_args()
if not args.display:
 parser.error('DISPLAY is unset; pass --display to avoid an unintended offscreen player.')
OUT=args.evidence.resolve();OUT.mkdir(parents=True,exist_ok=True)
assert not (OUT/'pid').exists(),'Use a new evidence folder for each launch.'
video=json.loads((ROOT/'unity/evidence/courtyard/20260908/after-native/settings.json').read_text())['video']
if args.capped:video['vSync']=True;video['frameLimit']=60
encoded=base64.b64encode(json.dumps(video).encode()).decode()
for vendor,product in [('unknown','unknown'),('Free Column','Athen Hill')]:
 p=OUT/'config/unity3d'/vendor/product;p.mkdir(parents=True,exist_ok=True)
 (p/'prefs').write_text('<?xml version="1.0" encoding="utf-8"?><unity_prefs version_major="1" version_minor="1"><pref name="AthenHill.Settings.v1.QA.Video" type="string">'+encoded+'</pref></unity_prefs>')
exe=ROOT/'unity/AthenHill/Builds/LinuxDevelopment/AthenHill.x86_64'
arguments=[str(exe),'-force-glcore','-screen-width','1920','-screen-height','1080','-screen-fullscreen','0','-logFile',str(OUT/'Player.log'),'--athen-qa',str(OUT)]
if args.background:arguments.append('--athen-qa-background')
p=subprocess.Popen(arguments,env=dict(os.environ,DISPLAY=args.display,XDG_CONFIG_HOME=str(OUT/'config')),stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT,start_new_session=True)
(OUT/'pid').write_text(str(p.pid))
for i in range(300):
 if p.poll() is not None:raise RuntimeError('Native player exited during startup')
 if (OUT/'snapshot.json').exists():break
 time.sleep(.2)
else:raise RuntimeError('Native bridge did not start')
print(json.dumps(dict(pid=p.pid,evidence=str(OUT))))
