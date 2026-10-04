# Primus MCP Server

The Primus MCP server exposes one programmable tool: `execute_tactus`.

Instead of publishing a separate MCP tool for every Primus operation, the server
runs short Tactus/Lua snippets inside a sandboxed runtime. The runtime injects
`primus` as a global host module, so agents can call Primus APIs
programmatically without repeating the import boilerplate:

```lua
return primus.score.info{
  scorecard_identifier = "Quality Assurance v1.0",
  score_identifier = "Compliance Check",
}
```

The MCP interface stays small while the Primus runtime surface can grow behind
the `primus` host module. This follows the broader Tactus
[One Tool For Everything](https://tactus.anth.us/use-cases/one-tool-programmable-api/)
pattern.

## Discovery

Start every session by discovering the available runtime API and docs from
inside `execute_tactus`:

```lua
return primus.api.list({})
```

```lua
return primus.docs.list({})
```

```lua
return primus.docs.get({ key = "mcp.execute-tactus-overview" })
```

Docs live under `documentation/agent/` and are exposed through
`primus.docs.*`. Each topic carries YAML frontmatter with `id`, `title`,
`summary`, `namespace`, `status`, `disclosure`, `tags`, and `related`.
The runtime rejects path traversal and unknown documentation ids.

## Common Calls

Run a local prediction:

```lua
return primus.score.predict{
  scorecard_identifier = "Quality Assurance v1.0",
  score_identifier = "Compliance Check",
  item_id = "item-123",
  yaml = true,
}
```

Find feedback items:

```lua
return primus.feedback.find{
  scorecard_name = "Quality Assurance v1.0",
  score_name = "Compliance Check",
  initial_value = "No",
  final_value = "Yes",
  limit = 5,
  days = 30,
}
```

Run a long evaluation with an async handle:

```lua
local handle = primus.evaluation.run{
  scorecard_name = "Quality Assurance v1.0",
  score_name = "Compliance Check",
  n_samples = 200,
  yaml = true,
  async = true,
  budget = {
    usd = 0.25,
    wallclock_seconds = 900,
    depth = 1,
    tool_calls = 20,
  },
}

return { evaluation_handle = handle }
```

Poll, await, or cancel a handle in a later `execute_tactus` call:

```lua
return primus.handle.await{ id = "<handle-id>", timeout = "PT10M" }
```

## Runtime Contract

`execute_tactus` returns a structured envelope with:

- `ok`: whether execution completed successfully
- `value`: the returned Lua/Tactus value, when successful
- `error`: structured error details, when unsuccessful
- `cost`: budget and usage information
- `api_calls`: Primus runtime calls made by the snippet
- `trace_id` and trace metadata for debugging

Long-running calls such as `primus.evaluation.run`, `primus.report.run`, and
`primus.procedure.run` require `async = true` with an explicit child `budget`.
Blocking calls that need handle semantics fail with a structured
`requires_handle_protocol` error.

## Claude Code Setup

Claude Code discovers MCP servers from `.mcp.json` at the project root.
This file is gitignored (per-user paths). Copy the example and update paths:

```bash
cp .mcp.json.example .mcp.json
# Edit .mcp.json — replace /path/to/ with your actual paths
```

Then in `.claude/settings.local.json`, enable the server:

```json
{
  "enabledMcpjsonServers": ["Primus"]
}
```

Restart Claude Code to connect.

## Server Entry Points

The main server entry point is `MCP/server.py`. It registers only
`execute_tactus`:

```bash
python MCP/server.py --transport stdio
```

Authenticated ASGI usage is wired through `MCP/asgi_app.py`.

## Adding Primus Capabilities

Do not add a new top-level MCP tool for each feature. Add capabilities to the
Tactus runtime instead:

1. Implement or wire the Primus SDK/service function.
2. Expose it through `MCP/tools/tactus_runtime/execute.py`, preferably as a
   direct handler.
3. Make it discoverable through `primus.api.list({})`.
4. Document the workflow under `documentation/agent/<namespace>/<topic>.md`
   with YAML frontmatter following the schema in `AGENTS.md`.
5. Add tests in `MCP/tools/tactus_runtime/execute_test.py`.

This keeps the external MCP schema stable while giving agents a richer,
composable programming surface.

## Related Runtime Docs

Discoverable through `primus.docs.*`:

- `mcp.execute-tactus-overview`
- `mcp.discovery`
- `mcp.handle-protocol`
- The `evaluation-feedback`, `score-authoring`, and `reports` namespaces.
