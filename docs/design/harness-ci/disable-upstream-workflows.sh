#!/usr/bin/env bash
#
# Selectively silence the 15 inherited upstream workflows in the ORACLE fork,
# without deleting a single tracked file.
#
# WHY NOT JUST DELETE THEM: design doc §1 pins this fork as a read-only oracle.
# Deleting upstream files means (a) the oracle is no longer byte-identical to
# Jellyfin, which other docs lean on, and (b) every future re-pin onto a newer
# upstream resolves 15 delete/modify conflicts. Per-workflow disable is repo
# STATE, not file state: zero diff, and it survives merges.
#
# WHEN YOU NEED THIS: only if Actions is enabled repo-wide on the fork. As of
# writing it is not — the API reports 15 workflows all with state "active" but
# zero workflow runs, ever, which is GitHub's default for forks. If you never
# enable Actions here, you never need this script.
#
# CAVEATS
#   * Requires Actions enabled repo-wide first; the endpoint 403s otherwise.
#   * Only affects workflows on the DEFAULT BRANCH.
#   * A re-pin that introduces NEW upstream workflow files brings them in
#     `active`. Re-run this after every pin bump.
#   * Scheduled workflows are already auto-disabled on forks, and again after
#     60 days of repo inactivity. Do not rely on that as your only guard.
#
# Usage:  ./disable-upstream-workflows.sh [--apply]
#         Dry-run by default. Requires `gh` authenticated with repo scope.

set -euo pipefail

REPO="${REPO:-erstaples/jellyfin}"
APPLY=false
[ "${1:-}" = "--apply" ] && APPLY=true

# Everything inherited from upstream. Keep this list exhaustive rather than
# clever: an allowlist of "ours" would silently re-enable anything new.
UPSTREAM_WORKFLOWS=(
  ci-codeql-analysis.yml
  ci-compat.yml
  ci-format.yml
  ci-tests.yml
  commands.yml
  issue-stale.yml
  issue-template-check.yml
  openapi-generate.yml
  openapi-merge.yml
  openapi-pull-request.yml
  openapi-workflow-run.yml
  project-automation.yml
  pull-request-conflict.yml
  pull-request-stale.yaml
  release-bump-version.yaml
)

# The five that would actually MISBEHAVE rather than merely waste minutes: they
# mutate issues, project boards, and releases, and one runs with elevated
# permissions. If you only silence a subset, silence these.
#   commands.yml               acts on issue comments
#   issue-stale.yml            closes issues
#   pull-request-stale.yaml    closes PRs
#   project-automation.yml     writes project boards
#   release-bump-version.yaml  bumps versions on release
#   pull-request-conflict.yml  uses pull_request_target (elevated permissions)

echo "repo: $REPO"
$APPLY || echo "DRY RUN — pass --apply to actually disable"
echo

for wf in "${UPSTREAM_WORKFLOWS[@]}"; do
  state="$(gh api "repos/$REPO/actions/workflows/$wf" --jq .state 2>/dev/null || echo MISSING)"
  if [ "$state" = "MISSING" ]; then
    echo "  SKIP     $wf (not registered)"
    continue
  fi
  if [ "$state" != "active" ]; then
    echo "  ALREADY  $wf ($state)"
    continue
  fi
  if $APPLY; then
    gh api -X PUT "repos/$REPO/actions/workflows/$wf/disable"
    echo "  DISABLED $wf"
  else
    echo "  WOULD    $wf (active)"
  fi
done

echo
echo "Verify with:"
echo "  gh api repos/$REPO/actions/workflows --jq '.workflows[] | \"\\(.state)\\t\\(.path)\"'"
