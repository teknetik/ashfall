"""Terminal screen art for Carl's Reclaim & Save Point kiosks (30 Sep 2026): follows the layout Meshy baked into his
model (header, record panel, map with a respawn pin) at a resolution that stays crisp at arm's length, with an honest
amber status line (there is no save or reclaim interaction in the game). Writes terminal_screen.svg and, through
rsvg-convert, unity/.../Art/HillProps/Terminal/Terminal_Screen.png (1024 x 680, alpha = rounded screen mask)."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[2] / "unity/AthenHill/Assets/AthenHill/Art/HillProps/Terminal/Terminal_Screen.png"
FONT = "Noto Sans"
W, H = 1024, 680
cy, dim, amber, ink = "#8ff0ff", "#3e8f9a", "#e2a64b", "#0a2328"

grid = "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#0e3a40" stroke-width="1"/>' for x in range(0, W, 32))
grid += "".join(f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#0e3a40" stroke-width="1"/>' for y in range(0, H, 32))
scan = "".join(f'<rect x="0" y="{y}" width="{W}" height="1" fill="#000" opacity="0.18"/>' for y in range(0, H, 4))
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
 <defs>
  <radialGradient id="bg" cx="50%" cy="45%" r="75%"><stop offset="0" stop-color="#0b3238"/><stop offset="1" stop-color="#03110f"/></radialGradient>
  <clipPath id="scr"><rect x="6" y="6" width="{W-12}" height="{H-12}" rx="46" ry="46"/></clipPath>
 </defs>
 <g clip-path="url(#scr)">
  <rect width="{W}" height="{H}" fill="url(#bg)"/>
  <g opacity="0.55">{grid}</g>
  <!-- header -->
  <rect x="40" y="34" width="{W-80}" height="74" rx="10" fill="#0f3f46" opacity="0.7"/>
  <text x="{W/2}" y="86" font-family="{FONT}" font-weight="900" font-size="46" fill="{cy}" text-anchor="middle" letter-spacing="3">RECLAIM &amp; SAVE POINT</text>
  <!-- record panel -->
  <rect x="40" y="130" width="420" height="400" rx="14" fill="{ink}" stroke="{dim}" stroke-width="3"/>
  <text x="64" y="176" font-family="{FONT}" font-weight="700" font-size="26" fill="{cy}" letter-spacing="2">COLONIST RECORD</text>
  <line x1="64" y1="192" x2="436" y2="192" stroke="{dim}" stroke-width="2"/>
  <rect x="64" y="214" width="110" height="130" rx="8" fill="#0d3339" stroke="{dim}" stroke-width="2"/>
  <circle cx="119" cy="258" r="26" fill="none" stroke="{cy}" stroke-width="5"/>
  <path d="M77 336 Q119 282 161 336" fill="none" stroke="{cy}" stroke-width="5"/>
  <text x="196" y="240" font-family="{FONT}" font-size="22" fill="{dim}">REGISTRY</text>
  <text x="196" y="270" font-family="{FONT}" font-weight="700" font-size="26" fill="{cy}">WARD · TIR</text>
  <text x="196" y="306" font-family="{FONT}" font-size="22" fill="{dim}">SECTOR</text>
  <text x="196" y="336" font-family="{FONT}" font-weight="700" font-size="26" fill="{cy}">THE HILL</text>
  <g font-family="{FONT}" font-size="24" fill="{cy}">
   <rect x="64" y="372" width="372" height="40" rx="6" fill="#12505a" opacity="0.8"/>
   <text x="80" y="400">◆  RECORD 01</text><text x="420" y="400" text-anchor="end" fill="{dim}">--:--</text>
   <text x="80" y="446">◇  RECORD 02</text><text x="420" y="446" text-anchor="end" fill="{dim}">EMPTY</text>
   <text x="80" y="492">◇  RECORD 03</text><text x="420" y="492" text-anchor="end" fill="{dim}">EMPTY</text>
  </g>
  <!-- map panel: Ward's walls, the avenue, the hill and its tree ring -->
  <rect x="484" y="130" width="500" height="400" rx="14" fill="{ink}" stroke="{dim}" stroke-width="3"/>
  <text x="508" y="176" font-family="{FONT}" font-weight="700" font-size="26" fill="{cy}" letter-spacing="2">WARD</text>
  <text x="960" y="176" font-family="{FONT}" font-size="22" fill="{dim}" text-anchor="end">GRID 04 · 17</text>
  <line x1="508" y1="192" x2="960" y2="192" stroke="{dim}" stroke-width="2"/>
  <g fill="none" stroke="{dim}" stroke-width="4">
   <path d="M530 222 L938 222 L938 506 L530 506 Z"/>
   <path d="M530 364 L938 364" stroke-width="10" stroke="#154a52"/>
   <path d="M734 222 L734 506" stroke-width="6" stroke="#154a52"/>
   <rect x="560" y="246" width="70" height="46"/><rect x="560" y="430" width="70" height="46"/>
   <rect x="840" y="246" width="70" height="46"/><rect x="840" y="430" width="70" height="46"/>
   <rect x="652" y="400" width="44" height="30"/><rect x="772" y="298" width="44" height="30"/>
  </g>
  <rect x="696" y="326" width="76" height="76" fill="#0e3a40" stroke="{cy}" stroke-width="4"/>
  <circle cx="734" cy="364" r="20" fill="none" stroke="{cy}" stroke-width="4"/>
  <path d="M734 300 C712 300 704 318 704 330 C704 350 734 372 734 372 C734 372 764 350 764 330 C764 318 756 300 734 300 Z" fill="{cy}"/>
  <circle cx="734" cy="330" r="10" fill="{ink}"/>
  <text x="508" y="520" font-family="{FONT}" font-size="20" fill="{cy}">● RESPAWN POINT · THE HILL</text>
  <!-- status bar -->
  <rect x="40" y="552" width="{W-80}" height="92" rx="12" fill="#1f1a0e" stroke="{amber}" stroke-width="3"/>
  <text x="70" y="596" font-family="{FONT}" font-weight="900" font-size="32" fill="{amber}" letter-spacing="2">LINK OFFLINE</text>
  <text x="70" y="630" font-family="{FONT}" font-size="22" fill="{amber}" opacity="0.85">Aquifer relay maintenance · records held locally</text>
  <text x="{W-70}" y="630" font-family="{FONT}" font-size="22" fill="{dim}" text-anchor="end">WARD PUBLIC SERVICES</text>
  <g>{scan}</g>
 </g>
</svg>'''
(HERE / "terminal_screen.svg").write_text(svg, encoding="utf-8")
OUT.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(["rsvg-convert", "-w", str(W), "-h", str(H), "-o", str(OUT), str(HERE / "terminal_screen.svg")], check=True)
print(OUT)
