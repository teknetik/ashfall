"""Run a C# method body file in the live Unity Editor via MCP execute_code (CodeDom C# 6 by default).
Usage: uv run --offline --with fastmcp python unity/tools/unity_exec.py body.cs [auto|roslyn|codedom]
The body may `return` a string. Relative paths inside the C# resolve from unity/AthenHill."""
import asyncio, json, sys, os
from fastmcp import Client
async def main():
    code = open(sys.argv[1]).read()
    compiler = sys.argv[2] if len(sys.argv) > 2 else 'auto'
    async with Client('http://127.0.0.1:18081/mcp', timeout=600) as c:
        await c.call_tool('set_active_instance', {'instance': os.environ.get('ATHEN_UNITY_INSTANCE', 'AthenHill@7f7f353bae1a07d0')})
        r = await c.call_tool('execute_code', {'action': 'execute', 'code': code, 'safety_checks': False, 'compiler': compiler}, raise_on_error=False)
        for part in r.content:
            t = getattr(part, 'text', None)
            if t is None: continue
            try:
                d = json.loads(t)
                if isinstance(d, dict) and 'data' in d and isinstance(d['data'], dict) and 'result' in d['data']:
                    res = d['data']['result']
                    print(res if isinstance(res, str) else json.dumps(res, indent=1))
                    extra = {k: v for k, v in d.items() if k != 'data'}
                    if not d.get('success', True): print(json.dumps(extra))
                else:
                    print(json.dumps(d, indent=1)[:20000])
            except Exception:
                print(t[:20000])
asyncio.run(main())
