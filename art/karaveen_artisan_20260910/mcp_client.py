#!/usr/bin/env python3
"""Small MCP stdio client for the pinned, locally installed Blender bridge.

Run with /tmp/ward-blender-mcp-20260910/venv/bin/python. JSON on stdout
contains the complete MCP result; --output also saves that receipt to a file.
The server executable is launched directly, never through a shell.
"""

import argparse
import asyncio
import json
import math
from pathlib import Path
import sys
import tempfile
import time


DEFAULT_SERVER = "/tmp/ward-blender-mcp-20260910/venv/bin/blender-mcp"


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--list", action="store_true", help="List exposed tools and schemas.")
    action.add_argument("--tool", metavar="NAME", help="Call an exposed tool.")
    action.add_argument("--code-file", type=Path, help="Call execute_blender_code with this UTF-8 source.")
    payload = parser.add_mutually_exclusive_group()
    payload.add_argument("--args", help="Tool arguments as a JSON object (default: {}).")
    payload.add_argument("--args-file", type=Path, help="Read the argument object from a JSON file.")
    parser.add_argument("--server-command", default=DEFAULT_SERVER,
                        help="One executable path; shell commands and arguments are not interpreted.")
    parser.add_argument("--timeout", type=float, default=120.0,
                        help="Total connection, initialization and operation timeout in seconds.")
    parser.add_argument("--output", type=Path, help="Also save the full JSON receipt to this file.")
    parser.add_argument("--server-log", type=Path,
                        help="Append server stderr here; default: a unique file in /tmp/ward-blender-mcp-20260910.")
    return parser.parse_args()


def error_detail(exc):
    detail = {"type": type(exc).__name__, "message": str(exc)}
    # AnyIO task groups can wrap the useful transport error in an ExceptionGroup.
    children = getattr(exc, "exceptions", None)
    if children:
        detail["causes"] = [error_detail(child) for child in children]
    return detail


async def request(options, state, tool, payload):
    # Defer optional imports so --help and syntax checks do not need the SDK.
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    server = StdioServerParameters(
        command=options.server_command, args=[], env={"DISABLE_TELEMETRY": "true"}
    )
    state["stage"] = "server_log"
    if options.server_log:
        log = options.server_log.resolve().open("a", encoding="utf-8")
    else:
        log_dir = Path("/tmp/ward-blender-mcp-20260910")
        log_dir.mkdir(parents=True, exist_ok=True)
        log = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="server-",
                                          suffix=".log", dir=log_dir, delete=False)
    state["server_log"] = str(Path(log.name).resolve())
    with log:
        state["stage"] = "connect"
        async with stdio_client(server, errlog=log) as (read, write):
            async with ClientSession(read, write) as session:
                state["stage"] = "initialize"
                await session.initialize()
                state["stage"] = "operation"
                state["request_started"] = True
                result = await session.list_tools() if options.list else await session.call_tool(tool, payload)
                # Preserve the wire field names and all text/structured/image content.
                result_data = result.model_dump(mode="json", by_alias=True, exclude_none=True)
                state["result"] = result_data
                state["stage"] = "disconnect"
    return result_data


def main():
    options = arguments()
    started = time.monotonic()
    state = {"stage": "validate", "request_started": False}
    tool = "execute_blender_code" if options.code_file else options.tool
    receipt = {"ok": False, "operation": "list_tools" if options.list else "call_tool"}
    if tool:
        receipt["tool"] = tool
    try:
        if not math.isfinite(options.timeout) or options.timeout <= 0:
            raise ValueError("--timeout must be a finite positive number")
        if not options.tool and (options.args is not None or options.args_file is not None):
            raise ValueError("--args and --args-file require --tool")
        if options.code_file:
            payload = {"code": options.code_file.read_text(encoding="utf-8")}
        else:
            source = options.args_file.read_text(encoding="utf-8") if options.args_file else options.args
            payload = json.loads(source) if source is not None else {}
            if not isinstance(payload, dict):
                raise ValueError("Tool arguments must be a JSON object")

        async def run():
            return await asyncio.wait_for(request(options, state, tool, payload), options.timeout)

        result = asyncio.run(run())
        receipt.update(ok=not bool(result.get("isError", False)), result=result)
        receipt["outcome"] = "tool_error" if result.get("isError", False) else "response_received"
    except (Exception, KeyboardInterrupt) as exc:
        receipt.update(error=error_detail(exc), stage=state["stage"])
        if "result" in state:
            receipt["result"] = state["result"]
            receipt["outcome"] = "response_received_cleanup_failed"
        else:
            # A timeout/disconnect after dispatch does not prove code was rolled back.
            receipt["outcome"] = "unknown" if state["request_started"] else "not_dispatched"
    receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
    if "server_log" in state:
        receipt["server_log"] = state["server_log"]
    if options.output:
        try:
            options.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError as exc:
            receipt["output_error"] = error_detail(exc)
            receipt["ok"] = False
    print(json.dumps(receipt, ensure_ascii=False, separators=(",", ":")))
    return 0 if receipt["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
