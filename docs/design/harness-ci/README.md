# Differential harness CI — staged drop-in

`differential.yml` is the GitHub Actions workflow for the differential harness specified in
`docs/analysis/07-harness-contract.md`.

**It is staged here, not installed.** It does not run in this repository and must not be moved
into `.github/workflows/` here. Two reasons:

1. **Wrong repo.** Design doc §1 pins this fork as a **read-only oracle**, consumed by the Go
   repo as a submodule at a tagged commit. The harness lives in the Go repo
   (`jellyfin-go/differential/`, §1 "Concrete layout"); its CI belongs there too. The value of
   "the oracle is not code we touch" evaporates if we start adding our own automation to it.
2. **Collision.** This fork already carries 15 upstream workflow files in `.github/workflows/`.
   Adding ours would fire on every push here and conflict on any future rebase onto upstream
   `master`.

## Destination

```
jellyfin-go/.github/workflows/differential.yml
```

## What must exist before it goes green

The workflow is written against the layout and CLI contract below. None of it exists yet — this
is the target, and the list doubles as the build order.

| Path | Role |
|:--|:--|
| `oracle/` | submodule → this fork, pinned at `oracle-v12.0.0` (design §1) |
| `differential/oracle-harness/JellyfinOracle.Harness.csproj` | the C# side (contract §2); NDJSON stdin→stdout |
| `differential/cmd/corpusgen` | fixtures → `corpus.ndjson`, deterministic (contract §4.4) |
| `differential/cmd/goside` | Go side; same NDJSON contract as the C# harness |
| `differential/cmd/diff` | normalization + comparison (contract §5) |
| `differential/cmd/coverage` | Gate 4 — pipelines and version gates exercised |
| `differential/normalization.json` | the §5 rules, version-controlled as contract |
| `differential/known-uncovered.md` | branches that cannot be covered, **asserted to match** |
| `fixtures/golden/oracle.ndjson` | oracle output at the pinned commit |
| `fixtures/golden/oracle-adversarial.ndjson` | Gate 6 escaping tier |

### Harness CLI contract

```
JellyfinOracle.Harness [--self-check-roundtrip] [--coverage-out FILE]  < corpus.ndjson > oracle.ndjson
```

One request object per line in, one response per line out, in order, `id` echoed (contract §2.1).
`--self-check-roundtrip` performs Gate 1 and writes nothing to stdout.

## Gate mapping

| Gate | Job / step | Status |
|:--|:--|:--|
| 0 — oracle baseline | `oracle` → *Gate 0* | discharged locally, 663/663 |
| 0b — golden drift | `oracle` → *Gate 0b* | needs goldens committed |
| 1 — protocol round-trip | `oracle` → *Gate 1* | partly discharged (§2.2) |
| 2 — host assertion | `host-assert` | implemented here |
| 3 — StreamBuilder zero-diff | `differential` | needs the Go side |
| 4 — corpus coverage | `oracle` → *Gate 4* | needs `corpusgen` |
| 5 — EncodingHelper zero-diff | `differential` | needs the Go side |
| 5a — argv without media/GPU | *(local)* | discharged |
| 6 — adversarial paths | `differential` | needs the Go side |
| 7 — CI wiring | this file | implemented here |

## Two decisions worth reading before editing

**Use `actions/setup-dotnet`, not the apt route.** The
`packages.microsoft.com` + `apt-get install dotnet-sdk-10.0` procedure recorded in contract §7
exists only because *this sandbox's* egress proxy blocks `builds.dotnet.microsoft.com`.
GitHub-hosted runners have no such restriction. Do not generalise the workaround into CI. The
parts that *do* carry over are `-c Release` (the Debug-only analyzer at
`Directory.Build.props:23-24`, which fails `CS9057` when the prebuilt analyzer targets a newer
Roslyn than the pinned SDK) and `submodules: recursive`.

**The host assertion transliterates the oracle's predicates — and a container would not help.**
`Environment.OSVersion.Version` on Linux reports the **host kernel**. Containers share the
host kernel, so running the job in a pinned image stabilises the userland and nothing else.
Asserting an exact kernel would break on every runner-image bump while buying no determinism.
Instead the job asserts *which side of each branching gate* the runner sits on, and fails
loudly if a bump moves it across one — because that changes which branches the corpus covers
and invalidates `known-uncovered.md`.

The i915 check is a **transliteration, not a range**. The real predicate at
`EncodingHelper.cs:2124-2126` is

```
isFixedKernel60 = major == 6 && minor == 0 && v >= 6.0.18
isUnaffected    = v < 5.18 || v > 6.1.3
affected        = !(isUnaffected || isFixedKernel60)
```

so `6.0.18 ≤ v < 6.1` is a **carve-out** — unaffected despite sitting inside `5.18..6.1.3`.
A naive range check marks those kernels affected and fails a healthy runner. The shell was
tested against `5.14 / 5.15 / 5.17.9 / 5.18 / 6.0.18 / 6.1.3 / 6.1.4 / 6.2 / 6.18.5` and
against suffixed release strings (`6.8.0-51-generic`). The other gate, the AMD Vulkan
modifier threshold at `:72`, is a plain `v >= 5.15`.

This supersedes the "pin a container image" suggestion made in review; it does not work.

## Why goldens are committed

The Go side diffs against `fixtures/golden/oracle.ndjson`, not against a live oracle run. That
is deliberate:

- A Go developer reproduces CI locally with no .NET toolchain.
- Oracle drift becomes its own gate (0b) with its own diff, instead of being smeared across
  every Go-side failure.
- The `differential` job stays fast and independent of the oracle build.

Regeneration is an explicit, reviewed act — `make regenerate-goldens` — never automatic.

## Selective execution

Two separate problems; they do not share a mechanism.

### In the Go repo — nothing to be selective against

No inherited workflows, so selectivity is only about not burning minutes:

- **`paths-ignore`, not `paths`.** A denylist fails safe. With an allowlist it is easy to
  omit an entry and silently skip the harness on a change that needed it — and if this
  workflow is ever a **required status check**, a path-skipped run never reports at all and
  the PR blocks forever with no way to satisfy it. `paths-ignore: ['docs/**', '**/*.md']`
  only skips when *every* changed file is documentation.
- **The oracle pin is not ignored.** A submodule appears to git as a single gitlink path
  (`oracle`), so bumping the pin is an ordinary file change and still triggers the run —
  which is the point, since Gate 0 and Gate 0b exist to catch exactly that.
- **Repository guard.** `if: github.repository == 'erstaples/jellyfin-go'` keeps forks from
  running a harness whose goldens they cannot regenerate.

### In the oracle fork — per-workflow disable, not deletion

Repo-level Actions enablement is all-or-nothing, so if you ever need something of ours to run
*here*, the selectivity comes from the per-workflow endpoint:

```
PUT /repos/{owner}/{repo}/actions/workflows/{id_or_filename}/disable
```

That is **repo state, not file state** — zero diff against upstream, and it survives merges.
`disable-upstream-workflows.sh` does this for all 15 (dry-run by default; `--apply` to
commit). Order of operations:

1. Enable Actions repo-wide (Settings → Actions → General).
2. Run `./disable-upstream-workflows.sh --apply`.
3. Only then add anything of ours.

**Current state, measured:** the API reports 15 workflows, every one `state: "active"`, and
**zero workflow runs ever**. So the per-workflow switches are all on and the repo-level toggle
is what is holding everything back — GitHub's default for forks. Nothing is firing today, and
none of this is needed until Actions is enabled here.

**Re-run the script after every oracle re-pin.** New upstream workflow files arrive `active`,
and the script's list is deliberately an exhaustive denylist rather than an allowlist of
"ours" — an allowlist would silently let anything new through.

If you only silence a subset, silence the ones that *mutate* state rather than merely waste
minutes: `commands.yml`, `issue-stale.yml`, `pull-request-stale.yaml`,
`project-automation.yml`, `release-bump-version.yaml`, and `pull-request-conflict.yml` — the
last of which runs on `pull_request_target`, the elevated-permission trigger.
