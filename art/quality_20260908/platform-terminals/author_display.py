"""Original, readable vector interface art; no generated lettering or gameplay claims."""
from pathlib import Path
import hashlib, json
from PIL import Image, ImageDraw, ImageFont
R=Path('/home/teknetik/code/ao2');O=R/'art/quality_20260908/platform-terminals/displays';O.mkdir(parents=True,exist_ok=True)
for variant,sub in [('SAVE','PROFILE ARCHIVE'),('RECLAIM','PROPERTY RETURN')]:
 svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" viewBox="0 0 1024 1024">
<rect width="1024" height="1024" fill="#071317"/>
<g fill="none" stroke="#315c61" stroke-width="3"><rect x="44" y="44" width="936" height="936" rx="22"/><path d="M76 224H948M76 790H948"/></g>
<g font-family="DejaVu Sans, sans-serif" fill="#a9e6df">
<text x="80" y="155" font-size="81" font-weight="bold" letter-spacing="5">{variant}</text>
<text x="82" y="196" font-size="25" letter-spacing="5">{sub}</text>
<g stroke="#638f91" stroke-width="9" fill="none"><rect x="414" y="306" width="196" height="156" rx="12"/><path d="M455 306V277Q512 204 569 277V306"/></g>
<text x="512" y="589" text-anchor="middle" font-size="79" font-weight="bold" letter-spacing="4" fill="#d1ae72">OFFLINE</text>
<text x="512" y="650" text-anchor="middle" font-size="29" letter-spacing="3">SERVICE UNAVAILABLE</text>
<text x="80" y="852" font-size="25" letter-spacing="4">WARD / PUBLIC SERVICES</text>
<text x="80" y="914" font-size="22" fill="#6d999b">Maintenance connection required</text>
</g></svg>'''
 # Screen graphics sit within the measured gasket opening; retain a dark glass margin.
 svg=svg.replace('<g fill="none"','<g transform="translate(52,76) scale(.8984375,.8515625)"><g fill="none"').replace('</g></svg>','</g></g></svg>')
 path=O/(variant.lower()+'.svg');path.write_text(svg)
 # Raster counterpart uses the same authored layout; no generated image is edited.
 im=Image.new('RGB',(1024,1024),'#071317');d=ImageDraw.Draw(im)
 d.rounded_rectangle((44,44,980,980),radius=22,outline='#315c61',width=3)
 d.line((76,224,948,224),fill='#315c61',width=3);d.line((76,790,948,790),fill='#315c61',width=3)
 def lettering(text,xy,size,color='#a9e6df',bold=False,center=False):
  font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)
  d.text(xy,text,font=font,fill=color,anchor='ms' if center else 'ls')
 lettering(variant,(80,155),81,bold=True);lettering(sub,(82,196),25)
 d.rounded_rectangle((414,306,610,462),radius=12,outline='#638f91',width=9)
 d.arc((455,237,569,336),180,360,fill='#638f91',width=9);d.line((455,287,455,306),fill='#638f91',width=9);d.line((569,287,569,306),fill='#638f91',width=9)
 lettering('OFFLINE',(512,589),79,'#d1ae72',True,True);lettering('SERVICE UNAVAILABLE',(512,650),29,center=True)
 lettering('WARD / PUBLIC SERVICES',(80,852),25);lettering('Maintenance connection required',(80,914),22,'#6d999b')
 padded=Image.new('RGB',(1024,1024),'#071317');padded.paste(im.resize((920,872),Image.Resampling.LANCZOS),(52,76));padded.save(O/(variant.lower()+'.png'))
plate=Image.new('RGBA',(1024,256),(0,0,0,0));d=ImageDraw.Draw(plate)
d.text((512,114),'WARD // SR-08',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',88),fill='#263132',anchor='ms')
d.text((512,189),'PUBLIC SERVICE TERMINAL',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',40),fill='#263132',anchor='ms');plate.save(O/'nameplate.png')
(O/'nameplate.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="256"><g font-family="DejaVu Sans" fill="#263132" text-anchor="middle"><text x="512" y="114" font-size="88" font-weight="bold">WARD // SR-08</text><text x="512" y="189" font-size="40">PUBLIC SERVICE TERMINAL</text></g></svg>')
files=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in sorted(O.glob('*'))if p.suffix in ['.svg','.png']]
(O/'manifest.json').write_text(json.dumps({'author':'Original Ward vector display art authored in this task','runtime_state':'Decorative OFFLINE screens; no save or reclaim implementation implied','files':files},indent=2))
