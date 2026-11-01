"""Run the crafting lane's release-bridge refusal check on this worktree."""
from pathlib import Path
source = Path('/home/teknetik/code/ao2-crafting/unity/evidence/crafting/20260928/independent-qa-rerun/check_release.py')
text = source.read_text().replace("OUT = HERE / 'release-native'", "OUT = Path(" + repr(str(Path(__file__).parent / 'release-native')) + ")")
fake = Path(__file__).resolve().parents[2] / 'crafting/20260928/independent-qa-rerun/check_release.py'
exec(compile(text, str(source), 'exec'), {'__file__': str(fake), '__name__': '__main__'})
