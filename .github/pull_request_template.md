## What changed

<!-- One or two sentences. What does this PR do, and which acceptance criterion does it serve? -->

## Which gate does this serve

<!-- Name the phase spec's acceptance criterion, ADR, or design contract this PR advances.
     A change that serves no named criterion is probably scope creep — say so if it is
     deliberate, and why. -->

## Receipts

Paste the **raw output** of the verification you ran — the command plus what it printed,
from this branch. A verdict or paraphrase is not a receipt.

```
$ make verify

<paste output here>
```

<!-- Until Phase 1 lands `make verify`, paste whatever checks apply: ruff, pyright,
     pytest, the def-token count, or the doc-link check. -->

## Checklist

- [ ] Serves a named acceptance criterion (or the deviation is flagged above)
- [ ] Verification output pasted above, from this branch
- [ ] Contracts in `docs/design/` still hold — or the change to them is in this PR
- [ ] Decisions that set direction are captured in `docs/adr/`
- [ ] `data_status` semantics preserved (`ok` / `empty_window` / `not_collected` /
      `partial` / `error`) — absence is never rendered as health
- [ ] No secrets in schemas, results, logs, or span attributes
