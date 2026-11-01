"""Fresh native reruns with existing real-keyboard harnesses and isolated evidence."""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
mode = sys.argv[1]
if mode == 'city':
    source = SOURCE / 'independent-qa/check_city.py'
    text = source.read_text().replace(
        "OUT = pathlib.Path(__file__).resolve().parent",
        "OUT = pathlib.Path(" + repr(str(HERE)) + ")",
    )
elif mode == 'crafting':
    source = SOURCE / 'check_crafting.py'
    text = source.read_text().replace(
        "OUT = Path(__file__).parent / 'native-smoke'",
        "OUT = Path(" + repr(str(HERE / 'crafting-native')) + ")",
    )
else:
    raise SystemExit('expected city or crafting')
exec(compile(text, str(source), 'exec'), {'__file__': str(source), '__name__': '__main__'})
