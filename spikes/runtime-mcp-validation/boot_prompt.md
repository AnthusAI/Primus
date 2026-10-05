# `execute_tactus`

Run a short Tactus snippet inside the Primus runtime. Use this as the only
tool for Primus work. The runtime injects everything you need before your
snippet runs:

- `primus` is already a global. You do **not** need
  `local primus = require("primus")`.
- The runtime captures the result of the **last** Primus operation your
  snippet calls and returns it as the value of this tool call. You only need
  to write an explicit `return` when the task asks for a custom output shape.
- Budget, streaming events, API call accounting, and HITL approval prompts
  are enforced by the runtime. You do not need to call
  `primus.budget.remaining()` or build approval flow yourself.
- Any long-running async call (`primus.evaluation.run`, `primus.report.run`,
  `primus.procedure.run` with `async = true`) must include an explicit child
  budget table:
  `budget = { usd = <number>, wallclock_seconds = <number>, depth = <int>, tool_calls = <int> }`.

The runtime also injects helper aliases. High-frequency short aliases include
`evaluate`, `predict`, `score`, `item`, `feedback`, `dataset`, `report`, and
`procedure`. Every advertised API also has a canonical `namespace_method`
helper, such as `scorecards_list`, `score_info`, `score_set_champion`,
`item_last`, `feedback_alignment`, `evaluation_info`, `evaluation_run`,
`dataset_check_associated`, `report_configurations_list`, `procedure_run`,
`handle_status`, `docs_get`, and `api_list`.

Use helpers when they fit. Fall back to `primus.<namespace>.<method>{...}` for
anything else.

Discover what you need instead of guessing API details from memory:

```tactus
local docs = primus.docs.list()
local scoring = primus.docs.get{ key = "score" }
local api = primus.api.list()
```

Prefer the cheapest reliable primitive. Use deterministic scores and aggregate
counts before LLM-backed investigation; use single predictions before full
evaluations; use sampled or bounded evaluations before broad runs unless the
user has asked for exhaustive work. The runtime enforces budget caps, but
choosing cheap primitives is still your job.

Always use table arguments, not positional arguments:

```tactus
local info = primus.score.info{ id = "score_compliance_tone" }
```

Destructive operations such as champion promotion, score updates, deletes, and
feedback invalidation request `Human.approve` automatically before mutating.
Only pass `no_confirm = true` when the user explicitly asked to bypass approval
or a higher-level approved workflow already handled it.

Errors are structured. If a Primus call fails, return the error code, message,
and retryability. Do not retry forever. Missing data is usually not retryable.

## Examples

Find a score and inspect its champion (explicit return shapes the result):

```tactus
local cards = primus.scorecards.list{ account = "Acme Health" }
for _, card in ipairs(cards) do
  local detail = primus.scorecards.info{ id = card.id }
  for _, s in ipairs(detail.scores) do
    if s.name == "Compliance Tone" then
      return {
        scorecard_id = card.id,
        score_id = s.id,
        score_name = s.name,
        champion_version_id = s.champion_version_id,
      }
    end
  end
end
return { error = { code = "SCORE_NOT_FOUND", retryable = false } }
```

Run one prediction (explicit return because the task wants custom fields):

```tactus
score{ id = "score_compliance_tone" }
item{ id = "item_1007" }
local prediction = predict{
  score_id = "score_compliance_tone",
  item_id = "item_1007",
}

return {
  item_id = prediction.item_id,
  score_id = prediction.score_id,
  score_version_id = prediction.score_version_id,
  predicted_value = prediction.value,
  explanation = prediction.explanation,
  cost = prediction.cost,
}
```

Run a bounded evaluation (no boilerplate; the runtime captures the result and
streams progress automatically):

```tactus
evaluate{
  score_id = "score_compliance_tone",
  item_count = 200,
}
```

Start long work asynchronously (still need explicit return to label the
follow-up call):

```tactus
local handle = evaluate{
  score_id = "score_compliance_tone",
  item_count = 1000,
  async = true,
  budget = {
    usd = 0.50,
    wallclock_seconds = 1800,
    depth = 1,
    tool_calls = 10,
  },
}

return {
  handle_id = handle.id,
  status = handle.status,
  check_later_with = "primus.handle.status",
}
```
