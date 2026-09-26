"""Live Blender MCP bake entry point: set FAMILY='Plaster' or 'MineralRunoff'.

Extract only the bake function; never rerun the one-time scene authoring step.
This works even if execute_code does not preserve Python names between calls.
"""
import ast
from pathlib import Path

_recipe_path = Path('/home/teknetik/code/ao2/art/reference_street_20260909/author_plaster.py')
_recipe = ast.parse(_recipe_path.read_text())
_function = next(n for n in _recipe.body
                 if isinstance(n, ast.FunctionDef) and n.name == 'bake_reference_plaster')
exec(compile(ast.Module(body=[_function], type_ignores=[]), str(_recipe_path), 'exec'))
bake_reference_plaster(FAMILY)
