# kit/kitload.py: import a kit module by FILE, whatever is ahead of kit/ on sys.path.
#
# Several families have their own check.py, review.py or measure.py. With such a folder ahead of kit/ on sys.path,
# "import check" runs that family's script in place of the kit's (20 Nov: a materials check ran pistol/check.py).
# The kit's own modules load each other through here, and a family script can do the same:
#
#   import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'kit'))
#   import kitload
#   check = kitload.load('check'); check.main(os.path.dirname(os.path.abspath(__file__)))
#
# The module is registered in sys.modules under its plain name when that name is free or already the kit's, so
# "import review as RV" elsewhere gets the same object (review.WARM and review.CARDS are module state). When another
# file already holds the plain name, the kit's is registered as 'kit_<name>'.
import importlib.util, os, sys

KIT = os.path.dirname(os.path.abspath(__file__))


def _is_kit(mod, path):
    f = getattr(mod, '__file__', None)
    return bool(f) and os.path.abspath(f) == path


def load(name):
    path = os.path.join(KIT, name + '.py')
    for key in (name, 'kit_' + name):
        m = sys.modules.get(key)
        if m is not None and _is_kit(m, path):
            return m
    key = name if name not in sys.modules else 'kit_' + name
    if KIT not in sys.path:
        sys.path.insert(0, KIT)
    spec = importlib.util.spec_from_file_location(key, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[key] = mod
    try:
        spec.loader.exec_module(mod)
    except BaseException:
        sys.modules.pop(key, None)
        raise
    return mod
