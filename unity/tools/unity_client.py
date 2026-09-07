"""Call the pinned, local Unity MCP through its real HTTP transport."""
import asyncio, json, sys, dataclasses
from fastmcp import Client

async def main():
    async with Client('http://127.0.0.1:18081/mcp', timeout=180) as client:
        action = sys.argv[1]
        group = 'testing' if action in ('run_tests','get_test_job') else 'profiling' if action=='manage_profiler' else 'ui' if action=='manage_ui' else None
        if group: await client.call_tool('manage_tools', {'action':'activate','group':group})
        if action not in ('tools', 'resource'):
            await client.call_tool('set_active_instance', {'instance':'AthenHill@7f7f353bae1a07d0'})
        if action == 'all-tools':
            for g in ['testing','profiling','ui']: await client.call_tool('manage_tools',{'action':'activate','group':g})
            result = [t.model_dump() for t in await client.list_tools()]
        elif action == 'tools':
            result = [t.model_dump() for t in await client.list_tools()]
        elif action == 'resource':
            result = await client.read_resource(sys.argv[2])
        elif action == 'batch':
            result = []
            for call in json.load(open(sys.argv[2])):
                response = await client.call_tool(call['tool'], call['args'])
                result.append({'tool':call['tool'], 'result':dataclasses.asdict(response)})
                payload = json.loads(response.content[0].text) if response.content and hasattr(response.content[0], 'text') else {}
                if response.is_error or payload.get('success') is False:
                    break
        else:
            args = json.loads(sys.argv[2]) if len(sys.argv)>2 else {}
            result = await client.call_tool(action, args)
        def encode(o):
            return o.model_dump() if hasattr(o,'model_dump') else dataclasses.asdict(o) if dataclasses.is_dataclass(o) else str(o)
        print(json.dumps(result,default=encode,indent=2))
asyncio.run(main())
