# ADR-0001: Agent layer as a separate repo, TowerWatch consumed as a domain source

- **Status:** Accepted
- **Date:** 2026-07-25
- **Deciders:** Anthony
- **Reversibility:** **Two-way door**, cheaply. Merging two repos later is a mechanical
  `git` operation; splitting a coupled monorepo later is not. Starting separate preserves
  both options.
- **Refs:** [`../specs/build-plan.md`](../specs/build-plan.md), [`../specs/spec-ai-native-repo-layer.md`](../specs/spec-ai-native-repo-layer.md), [ADR-0002](0002-dual-mode-data-access-via-protocol.md)

## Context and problem statement

TowerWatch is an existing, working network-monitoring project with real collected data,
its own deploy path onto Raspberry Pis, and its own operational history. This project
layers an agent surface — an MCP server, evals, a router — over that domain.

The layering could live inside TowerWatch or beside it. The choice had to be made before
any file was written, because it determines the dependency direction and therefore what
each side is allowed to assume about the other.

## Decision drivers

- **TowerWatch is a running system with a live deployment.** Changes to it carry
  operational risk that has nothing to do with the agent work.
- **The agent layer is the artifact being showcased.** Its repo is meant to be read as a
  demonstration of agent engineering; a reader should not have to separate agent code from
  three years of monitoring code to find it.
- **Different release cadences.** TowerWatch changes when the network setup changes. The
  agent layer changes on a three-phase build schedule.
- **Dependency direction should be one-way.** The agent layer reads TowerWatch's data
  model; TowerWatch should gain no knowledge of the agent layer at all.

## Options considered

### Option A — separate repo, TowerWatch as domain source of truth (chosen)

- **Pros:** TowerWatch stays untouched, so no agent work can destabilize a running
  monitoring deployment. The showcase repo contains only the work being showcased. The
  dependency is one-way and obvious. Each repo keeps its own release cadence.
- **Cons:** The domain model is documented in one repo and consumed in another, so a
  TowerWatch schema change can silently invalidate an assumption here. Cross-repo
  references (`../towerwatch/docs/metrics-inventory.md`) are not resolvable links on
  GitHub.

### Option B — add the agent layer inside TowerWatch

- **Pros:** One clone. Domain changes and their agent-side consequences land in one commit.
  No cross-repo reference problem.
- **Cons:** Every agent-layer experiment touches the repo that runs the actual monitoring.
  The showcase story gets buried in an existing codebase with unrelated history. Forces one
  release cadence on two things that change for different reasons.
- **Why not:** the operational risk is the decider. Nothing about the agent build should be
  able to break data collection.

### Option C — extract a shared domain package consumed by both

- **Pros:** A real, versioned contract between domain and agent layers. The drift risk in
  Option A gets a compile-time answer.
- **Why not:** premature at two repos and one author. It adds a publish step and a version
  matrix to solve a problem that has not yet been felt.

## Decision

**Option A.** The agent layer lives in `towerwatch-ops-agent`; TowerWatch is untouched and
treated as the domain source of truth. When tool design needs to know what data exists, the
answer comes from reading TowerWatch's `docs/architecture.md`,
`docs/metrics-inventory.md`, and `docs/runbook.md` — never from inventing metrics
TowerWatch does not collect.

## Consequences

- **Positive:** the monitoring deployment carries zero risk from this build. The showcase
  repo reads cleanly as one coherent project. Dependency direction is unambiguous.
- **Negative / trade-offs:** domain drift is possible and nothing catches it
  automatically — a TowerWatch metric rename would surface here as a runtime failure, not
  a build break. The curated fixture ([ADR-0002](0002-dual-mode-data-access-via-protocol.md))
  partially mitigates this by pinning the shape the agent layer expects, and pushes the
  detection to test time.
- **Follow-ups:** if drift becomes real rather than theoretical, revisit Option C.

## Links

- [ADR-0002](0002-dual-mode-data-access-via-protocol.md) — how this repo actually reaches
  TowerWatch's data.
- [`../../CLAUDE.md`](../../CLAUDE.md) — states the TowerWatch-as-domain-truth rule for agents.
