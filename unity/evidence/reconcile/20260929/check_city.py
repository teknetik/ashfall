"""Run the independently passing real-keyboard city route against integrated binary."""
from pathlib import Path
source = Path('/home/teknetik/code/ao2-crafting/unity/evidence/crafting/20260928/independent-qa/check_city.py')
text = source.read_text().replace("OUT = pathlib.Path(__file__).resolve().parent", "OUT = pathlib.Path(" + repr(str(Path(__file__).parent)) + ")")
fake = Path(__file__).resolve().parents[2] / 'crafting/20260928/independent-qa/check_city.py'
exec(compile(text, str(source), 'exec'), {'__file__': str(fake), '__name__': '__main__'})
