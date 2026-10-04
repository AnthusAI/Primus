import Link from "next/link";

const clientConfig = `{
  "mcpServers": {
    "primus": {
      "command": "/path/to/python",
      "args": [
        "/path/to/Primus/MCP/primus_fastmcp_wrapper.py",
        "--transport", "stdio",
        "--target-cwd", "/path/to/Primus"
      ],
      "env": {
        "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": "/path/to/Primus"
      }
    }
  }
}`;

const discoverSnippet = `return {
  apis = primus.api.list(),
  docs = primus.docs.list(),
  overview = primus.docs.get{ id = "mcp.execute-tactus-overview" },
}`;

const scoreSnippet = `return primus.score.info{
  scorecard_identifier = "Quality Assurance",
  score_identifier = "Compliance",
}`;

const feedbackSnippet = `local summary = primus.feedback.alignment{
  scorecard_name = "Quality Assurance",
  score_name = "Compliance",
  days = 30,
  output_format = "json",
}

local false_negatives = primus.feedback.find{
  scorecard_name = "Quality Assurance",
  score_name = "Compliance",
  initial_value = "No",
  final_value = "Yes",
  limit = 5,
  days = 30,
}

return {
  summary = summary,
  false_negatives = false_negatives,
}`;

const asyncSnippet = `local handle = primus.evaluation.run{
  scorecard_name = "Quality Assurance",
  score_name = "Compliance",
  n_samples = 200,
  yaml = true,
  async = true,
  budget = {
    usd = 1.0,
    wallclock_seconds = 900,
    depth = 1,
    tool_calls = 20,
  },
}

return {
  handle_id = handle.id,
  status = handle.status,
}`;

const handleSnippet = `return primus.handle.await{
  id = "<handle-id>",
  timeout = "PT10M",
}`;

function CodeBlock({ children }: { children: string }) {
  return (
    <pre className="bg-muted rounded-lg mb-4 overflow-x-auto p-4 text-sm">
      <code>{children}</code>
    </pre>
  );
}

export default function McpServerPage() {
  return (
    <div className="max-w-4xl mx-auto py-8 px-6">
      <h1 className="text-4xl font-bold mb-4">Primus MCP / Tactus Runtime</h1>
      <p className="text-lg text-muted-foreground mb-8">
        Connect an MCP client to Primus through one programmable tool:
        <code> execute_tactus</code>. The tool runs sandboxed Tactus snippets
        that call the host-provided <code>primus</code> runtime module.
      </p>

      <div className="space-y-8">
        <section>
          <h2 className="text-2xl font-semibold mb-4">Why one tool?</h2>
          <p className="text-muted-foreground mb-4">
            Earlier MCP integrations often exposed every application operation
            as a separate tool. That works for small systems, but Primus has a
            broad surface area: scorecards, scores, feedback, evaluations,
            reports, datasets, procedures, documentation, budgets, and handles.
            Loading all of that as individual tool schemas consumes model
            context on every call, adding latency and cost while displacing the
            user task and other useful context.
          </p>
          <p className="text-muted-foreground mb-4">
            Primus now exposes a compact gateway instead. The MCP client calls
            <code> execute_tactus</code>, and the submitted Tactus code composes
            the <code>primus</code> APIs it needs for the current task. The
            assistant writes a small program instead of choosing from a long
            menu of fine-grained tools.
          </p>
          <p className="text-muted-foreground mb-4">
            The gateway also supports progressive disclosure. The base MCP
            context only needs to describe <code>execute_tactus</code> and the
            discovery path: use <code>primus.api.list()</code> to inspect the
            available API surface, then use <code>primus.docs.list()</code> and{" "}
            <code>primus.docs.get{"{ ... }"}</code> to load focused docs and
            examples for the workflow at hand.
          </p>
          <p className="text-muted-foreground">
            This is the same pattern described on the Tactus site:{" "}
            <Link
              href="https://tactus.anth.us/use-cases/one-tool-programmable-api/"
              className="text-primary hover:underline"
            >
              One Tool For Everything
            </Link>
            .
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">Runtime model</h2>
          <p className="text-muted-foreground mb-4">
            Inside <code>execute_tactus</code>, <code>primus</code> is
            available as an injected global host module. It delegates to Primus
            SDK code, services, documentation, task dispatch, and handle
            storage. The Tactus runtime provides the controlled execution
            boundary around those calls.
          </p>
          <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
            <li>
              Use <code>primus.api.list()</code> to discover namespaces and
              methods.
            </li>
            <li>
              Use <code>primus.docs.list()</code> and{" "}
              <code>primus.docs.get{"{ ... }"}</code> to read focused docs
              during the session.
            </li>
            <li>
              Use explicit <code>return</code> values when you want a custom
              result shape.
            </li>
            <li>
              Long-running calls can return handles that are polled, awaited,
              or cancelled later.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">Client setup</h2>
          <p className="text-muted-foreground mb-4">
            Configure your MCP client to launch the Primus wrapper from your
            local Primus checkout. Replace the placeholder paths with your
            Python environment and project path.
          </p>
          <CodeBlock>{clientConfig}</CodeBlock>
          <p className="text-muted-foreground">
            Credentials are loaded from your Primus environment and config
            files. Keep API keys on the host side; they are not passed into the
            Tactus snippet.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">Start with discovery</h2>
          <p className="text-muted-foreground mb-4">
            When unsure what the runtime supports, ask Primus from inside the
            runtime instead of guessing tool names.
          </p>
          <CodeBlock>{discoverSnippet}</CodeBlock>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">Common examples</h2>
          <p className="text-muted-foreground mb-4">
            Inspect a score by scorecard and score identifiers:
          </p>
          <CodeBlock>{scoreSnippet}</CodeBlock>

          <p className="text-muted-foreground mb-4">
            Combine feedback summary and item search in one call:
          </p>
          <CodeBlock>{feedbackSnippet}</CodeBlock>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">Async handles and budgets</h2>
          <p className="text-muted-foreground mb-4">
            Evaluations, reports, and procedures can be long-running. Use
            <code> async = true</code> to dispatch the work and return a handle.
            Include an explicit child budget so background work remains bounded.
          </p>
          <CodeBlock>{asyncSnippet}</CodeBlock>

          <p className="text-muted-foreground mb-4">
            Later, use the handle APIs from another <code>execute_tactus</code>
            call:
          </p>
          <CodeBlock>{handleSnippet}</CodeBlock>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">Safety contract</h2>
          <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
            <li>
              The MCP surface stays small: clients only need to know{" "}
              <code>execute_tactus</code>.
            </li>
            <li>
              The runtime returns structured envelopes with success, value,
              error, cost, trace, partial, and API-call data.
            </li>
            <li>
              Destructive operations request human approval before committing
              changes.
            </li>
            <li>
              Traces and handles let operators inspect what happened and resume
              long-running work.
            </li>
            <li>
              Primus keeps credentials, SDK implementation, policy, and
              persistence on the trusted host side.
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-2xl font-semibold mb-4">Troubleshooting</h2>
          <ul className="list-disc pl-6 space-y-2 text-muted-foreground">
            <li>
              If the MCP client cannot connect, verify the Python path, wrapper
              path, <code>--target-cwd</code>, and <code>PYTHONPATH</code>.
            </li>
            <li>
              If a Primus call fails, inspect the returned structured error and
              trace ID before retrying.
            </li>
            <li>
              If a snippet needs a capability you cannot find, call{" "}
              <code>primus.api.list()</code> and then read the relevant docs
              with <code>primus.docs.get{"{ id = \"...\" }"}</code>.
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}
