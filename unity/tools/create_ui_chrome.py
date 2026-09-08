"""Original, editable SVG source for the colony HUD; render with CairoSVG.

No source screenshot pixels are used. Nine-slice borders preserve authored corners.
"""
from pathlib import Path
import random
import cairosvg

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / 'unity/AthenHill/Assets/AthenHill/UI/Art'
SOURCE = ROOT / 'refs/ui_20260908/chrome'
SOURCE.mkdir(parents=True, exist_ok=True)
ART.mkdir(parents=True, exist_ok=True)

def save(name, body, size=128):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 128 128">{body}</svg>'
    p = SOURCE / (name + '.svg')
    p.write_text(svg)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(ART / (name + '.png')))

def outline(inset, cut):
    a, b, c = inset, 128-inset, cut
    return f'M {a+c},{a} H {b-c} L {b},{a+c} V {b-c} L {b-c},{b} H {a+c} L {a},{b-c} V {a+c} Z'

random.seed(711)
for name, accent in [('frame', '#a48a62'), ('button', '#718080'), ('button-focus', '#58d5d7')]:
    frame = name == 'frame'
    parts = ['''<defs>
    <linearGradient id="metal" x2="0.3" y2="1"><stop stop-color="#d1b186"/><stop offset=".19" stop-color="#75674f"/><stop offset=".54" stop-color="#b79769"/><stop offset=".8" stop-color="#635b48"/><stop offset="1" stop-color="#9e774b"/></linearGradient>
    <linearGradient id="enamel" x2=".7" y2="1"><stop stop-color="#273030"/><stop offset=".28" stop-color="#141d1e"/><stop offset="1" stop-color="#202525"/></linearGradient>
    </defs>''']
    for inset, cut, fill, stroke, width in [(1,10,'#070e10','#0a1010',2),(3,9,'url(#metal)','#b8a782',.7),(5,8,'#182223','#080e0e',1),(7,7,'none',accent,1),(9,6,'url(#enamel)','#080e0e',1),(11,5,'none','#52605c',.6)]:
        parts.append(f'<path d="{outline(inset,cut)}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
    parts += ['<path d="M16 12 H111 M12 16 V109" stroke="#aab4a5" stroke-opacity=".22" fill="none"/>', '<path d="M17 116 H111 L116 111 V18" stroke="#020707" fill="none"/>']
    if name == 'button-focus':
        parts.append(f'<path d="{outline(8,7)}" fill="none" stroke="#59e5e6" stroke-opacity=".3" stroke-width="5"/>')
        parts.append(f'<path d="{outline(7,7)}" fill="none" stroke="#82f2ed" stroke-width="1.5"/>')
    if frame:
        for x,y,rot in [(4,4,0),(124,4,90),(124,124,180),(4,124,270)]:
            parts.append(f'<g transform="translate({x} {y}) rotate({rot})"><path d="M0 14 V6 L6 0 H25 V3 H8 L3 8 V25 H0" fill="#4a5a56" stroke="#080f0f"/><path d="M1 13 V7 L7 1 H24" fill="none" stroke="#a0aaa0" stroke-width=".7"/><path d="M6 8 L8 6" stroke="#d1b987"/></g>')
        for _ in range(95):
            x, y = random.uniform(14,114), random.uniform(14,114)
            parts.append(f'<path d="M{x:.2f} {y:.2f} l{random.uniform(1,8):.2f} -0.7" stroke="#b8b293" stroke-opacity="{random.uniform(.025,.095):.3f}" stroke-width=".4"/>')
        for _ in range(65):
            t=random.uniform(18,110)
            x,y=(t,random.choice([3.8,6.8,121.2,124.2])) if random.random()<.5 else (random.choice([3.8,6.8,121.2,124.2]),t)
            parts.append(f'<path d="M{x:.2f} {y:.2f} l1 -.6" stroke="{random.choice(["#e1c79a","#050d10"])}" stroke-opacity=".65" stroke-width=".7"/>')
        for x in (23,105):
            parts.append(f'<path d="M{x} 5 v2 M{x} 121 v2" stroke="#dcc7a1" stroke-width="1"/>')
    save(name, ''.join(parts))

save('insignia', '<g fill="#dddcd0"><path d="M58 12 L65 6 V119 L58 111Z M44 27 L51 19 V104 L44 97Z M30 45 L37 37 V89 L30 83Z M72 19 L79 27 V104 L72 112Z M86 37 L93 45 V89 L86 97Z M8 75 L23 53 V82Z M100 53 L117 75 L100 82Z"/></g>')
save('talk', '<g fill="none" stroke="#c9cfca" stroke-width="7" stroke-linejoin="round"><path d="M22 23 H104 Q111 23 111 31 V80 Q111 88 103 88 H58 L36 108 V88 H22 Q14 88 14 80 V31 Q14 23 22 23Z"/></g><g fill="#c9cfca"><circle cx="40" cy="55" r="5"/><circle cx="63" cy="55" r="5"/><circle cx="86" cy="55" r="5"/></g>')
save('diamond', '<path d="M64 12 L109 64 L64 116 L19 64Z" fill="#133d40" stroke="#73e8e4" stroke-width="6"/><path d="M64 30 L93 64 L64 98 L35 64Z" fill="#5be0dc"/>')
save('diamond-empty', '<path d="M64 15 L107 64 L64 113 L21 64Z" fill="none" stroke="#c0c6ba" stroke-width="6"/>')
save('inventory', '<g fill="#d3d7cc" stroke="#202828" stroke-width="4"><path d="M17 34 L63 14 L111 34 L64 54Z"/><path d="M17 40 L59 60 V113 L17 90Z"/><path d="M68 60 L111 40 V90 L68 113Z"/></g>')
save('coins', '<g stroke="#202828" stroke-width="4" fill="#c2c9bd"><path d="M25 64 V93 C25 115 104 115 104 93 V64Z"/><ellipse cx="64" cy="64" rx="39" ry="14"/><path d="M19 42 V70 C19 90 98 90 98 70 V42Z"/><ellipse cx="59" cy="42" rx="39" ry="14"/><path d="M26 23 V48 C26 67 104 67 104 48 V23Z"/><ellipse cx="65" cy="23" rx="39" ry="14"/></g>')
save('journal', '<path d="M33 15 H102 V115 H33Z" fill="none" stroke="#d2d4c8" stroke-width="7"/><path d="M43 17 V114 M52 39 H87 M52 52 H87 M52 65 H87 M52 78 H78" fill="none" stroke="#d2d4c8" stroke-width="5"/>')
parts=['<g fill="#c7cfc3">']
for angle in range(0,360,45):parts.append(f'<path d="M54 7 H74 L78 30 H50Z" transform="rotate({angle} 64 64)"/>')
parts+=['<path fill-rule="evenodd" d="M106 64 A42 42 0 1 1 22 64 A42 42 0 1 1 106 64 M80 64 A16 16 0 1 0 48 64 A16 16 0 1 0 80 64"/></g>']
save('gear',''.join(parts))
print('Original frame and symbol artwork rendered into', ART)
