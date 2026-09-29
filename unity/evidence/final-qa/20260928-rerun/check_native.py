"""Rerun existing independent native checks into this dated evidence directory."""
import sys
from pathlib import Path

HERE = Path(__file__).parent
NAME = sys.argv[1]
assert NAME in ('crafting', 'city', 'release')
source = HERE.parent / '20260928' / f'check_{NAME}.py'
text = source.read_text()
# Its own __file__ selects a fresh output directory while preserving the proven test body.
exec(compile(text, str(source), 'exec'), {'__file__': str(HERE / f'check_{NAME}.py'), '__name__': '__main__'})
