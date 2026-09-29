"""Run existing native harnesses without overwriting prior evidence."""
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
UNITY = HERE.parents[3]
mode = sys.argv[1]
if mode == 'city':
    source = HERE.parent / 'independent-qa/check_city.py'
    text = source.read_text().replace("OUT = pathlib.Path(__file__).resolve().parent", "OUT = pathlib.Path(" + repr(str(HERE)) + ")")
else:
    source = HERE.parent / 'check_crafting.py'
    text = source.read_text().replace("OUT = Path(__file__).parent / 'native-smoke'", "OUT = Path(" + repr(str(HERE / 'crafting-native')) + ")")
exec(compile(text, str(source), 'exec'), {'__file__': str(source), '__name__': '__main__'})
