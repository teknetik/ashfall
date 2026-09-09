"""Repeat all six source inspection angles for the corrected store sources."""
from pathlib import Path
p=Path('/home/teknetik/code/ao2/art/quality_20260909/relay-family/review_store_variants.py')
exec(compile(p.read_text().replace("store-variants-01", "store-variants-02"),str(p),'exec'))
