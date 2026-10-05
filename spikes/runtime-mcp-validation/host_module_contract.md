# Tactus Host Module Contract

This spike assumes Primus will be exposed to Tactus as an explicit host module,
not as part of the Tactus standard library.

## Host Registration

Production code should register the Primus capability module on a runtime before
executing user-supplied Tactus code:

```python
runtime.register_python_module("primus", primus_module)
```

Tactus code then imports Primus with the ordinary Tactus `require` mechanism:

```tactus
local primus = require("primus")
```

The `primus` name is an explicit host capability. It must not be discoverable via
arbitrary Python imports, filesystem paths, or the Tactus standard library.

## Required Tactus Behavior

- Host module names are validated as dotted identifiers.
- Host modules cannot use the reserved `tactus.*` namespace.
- Explicit host modules resolve before local `.tac` files, so `primus.tac` cannot
  shadow `require("primus")`.
- Tactus stdlib Python modules remain fallback behavior after `.tac` searchers,
  preserving existing Tactus-first semantics for `tactus.*`.
- Re-registering a host module clears Tactus's require cache for that module.

## Spike Harness Shim

The current harness uses a direct Lupa shim for `require("primus")` because the
host-module API is being developed in Tactus first. The Tactus-side contract is
already the same as production:

```tactus
local primus = require("primus")
```

Once Primus depends on a Tactus version with host modules, the shim should be
removed and replaced with `runtime.register_python_module("primus", ...)`.
