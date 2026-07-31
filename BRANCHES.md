# Branch map: how the annotation history is organized

This repository's real value is its git history — the record of every correction, alignment
fix, and annotation-style decision made against the MuseScore/MusicXML sources. That history
does **not** live on a single linear trunk. Different rounds of work (system/page-break
alignment, tie-as-dot annotation style, per-score manual corrections, external OMR-pipeline
submissions, versioned release snapshots) were each done on their own branch, by different
contributors, using different and sometimes mutually-incompatible conventions.

These branches are **intentionally divergent alternatives, not superseded work-in-progress**.
They are kept unmerged on purpose so that each approach remains individually inspectable and
reproducible. Only two branches have actually been merged into the trunk (`omr-dev` and, before
it, `main`); everything else is preserved as a parallel line of history. Squashing or merging
them together would destroy exactly the thing this repo exists to preserve: which score was
touched, by which approach, when, and why.

As of this writing, the default/release branch is **`omr-dev`** (which has just absorbed
`ossq-v2.4.0` via squash-merge and now carries the current release state), and
**`ossq-v2.4.0`** continues on as the active working line for OSSQ v2.4.x development.

## Branch inventory

Counts below were produced by running `git log <branch> --not main --oneline | wc -l`
("unique commits", i.e. commits reachable from the branch but not from `main`, the outdated
early skeleton every branch forked from) against a full clone with all remote branches fetched.
"Total" is every commit reachable from the branch tip. Date ranges cover only the unique
commits. Branches `crawl-imslp` and `fix-break-align`, mentioned in earlier discussions, were
deleted before this table was finalized and are intentionally omitted.

| Branch | Role / theme | Unique commits | Total commits | Date range | Merged into trunk? |
|---|---|---:|---:|---|---|
| `ossq-v2.4.0` | Active working line for OSSQ v2.4.x; was the trunk at time of writing | 38 | 46 | 2025-05-20 → 2026-07-31 | — (is the trunk) |
| `omr-dev` | Default branch; OMR processing line. Now the default/release branch after squash-merging `ossq-v2.4.0` | 21 | 29 | 2025-05-20 → 2026-03-29 | **Yes** (ancestor of `ossq-v2.4.0`) |
| `align-pt2` | System & page-break alignment across many scores (PR #2: 20 scores); largest single alignment branch by commit count | 115 | 123 | 2025-05-20 → 2026-02-11 | No |
| `merge-vissem-align` | Consolidation branch bringing together `vissem-align` plus review PRs #2, #5, #6, #7, #8 | 110 | 118 | 2025-05-20 → 2026-03-31 | No |
| `vissem-align` | Ties-as-dots annotation style; score-by-score review and correction passes | 86 | 94 | 2025-05-20 → 2026-03-13 | No |
| `align-brian` | Per-score individual corrections (system/line-break alignment, missing notes, misc fixes) | 67 | 75 | 2025-05-20 → 2026-02-09 | No |
| `preprocess` | OMR preprocessing-pipeline build-out plus alignment work (PR #5: 61 scores) | 48 | 56 | 2025-05-20 → 2026-02-11 | No |
| `sqamt` | OMR preprocessing-pipeline development (LMXE format, MuseScore headless rendering, bbox extraction) — an earlier snapshot that `preprocess` builds on | 39 | 47 | 2025-05-20 → 2026-02-09 | No |
| `add-break-align` | Break-alignment fixes prior to `ossq-v2.4.0`, incorporating PR #9 (`vissem-align` review/merge) | 36 | 44 | 2025-05-20 → 2026-04-01 | No |
| `omr-v2.3` | Version snapshot (PR #6, `ossq v2.3.0`) | 27 | 35 | 2025-05-20 → 2026-03-16 | No |
| `v2.3.1` | Release snapshot (PR #7); diverges from `v2.3.2` | 20 | 28 | 2025-05-20 → 2026-03-16 | No |
| `v2.3.2` | Release snapshot (PR #8); diverges from `v2.3.1` | 20 | 28 | 2025-05-20 → 2026-03-29 | No |
| `maler` | IMSLP crawling logic (PR #1) | 1 | 9 | 2025-05-20 | No |
| `main` | Outdated early skeleton; **not** the working trunk | — | 8 | 2023-09-26 → 2024-05-13 | root ancestor of every branch above |

Across all of these refs there are **298 commits total**, of which **290 are unreachable from
`main`** — i.e. the large majority of this repository's history lives off the outdated skeleton
branch entirely, spread across the divergent lines above.

## How to trace a score's history

A normal `git clone` already fetches every branch as a remote-tracking ref (`origin/<branch>`),
so `git log --all` works immediately with no extra setup:

```sh
git clone https://github.com/MALerLab/ossq-omr.git && cd ossq-omr
git log --all --source --oneline -- "scores/Beethoven,_Ludwig_van/String_Quartet_No.1,_Op.18_No.1/sq8071278.mscx"
git show <commit>
```

The `--source` flag labels which ref each commit came from, e.g.:

```
3403cc47 refs/heads/ossq-v2.4.0 PR: (#9) Review and Merge `vissem-align` branch
1c616446 refs/remotes/origin/vissem-align beethoven 18 1: vissem align
e99137c0 refs/heads/omr-dev PR: (#5) System and Page Break Alignment for 61 scores
6a5e0c3b refs/heads/omr-dev PR: (rebased) IMSLP crawling results
3b48d538 refs/heads/preprocess PR: (#5) System and Page Break Alignment for 61 scores
6543b995 refs/remotes/origin/align-pt2 beethoven 1 1: sys and lb align
91ce407e refs/heads/maler PR: (#1) IMSLP crawling logics
f535100d refs/heads/main Initial commit
```

That single command shows this score was touched on `main`, `maler`, `preprocess`, `omr-dev`,
`align-pt2`, `vissem-align`, and finally reviewed and merged into `ossq-v2.4.0` — the full
provenance chain, in one line each. Use `git show <commit>` to see the actual diff for any of
those commits.

## Thematic search

Because branch names and commit messages describe *what kind* of work was done (alignment,
review, per-score fixes, etc.), you can search across all branches at once:

```sh
git log --all --grep='align' --oneline
```

This currently returns **154 commits** across all branches, spanning the alignment-focused
work on `align-pt2`, `align-brian`, `add-break-align`, `preprocess`, and the alignment PRs
folded into `merge-vissem-align`.

You can also render the full shape of the history with:

```sh
git log --all --oneline --graph
```

Be warned: this prints roughly 300+ lines (one per commit, plus graph-edge padding) and, with
14 divergent branches sharing a handful of common ancestors, the ASCII graph is dense and not
easy to read in a terminal. It's more useful piped into a pager (`| less`) or a graphical git
history viewer than read top-to-bottom.

## GitHub's web UI does not show this

**GitHub's web blame and history views only ever show the default branch.** Browsing a file on
github.com and clicking "History" will show you the commits reachable from `omr-dev` (the
default branch) — none of the divergent work on `align-pt2`, `vissem-align`, `align-brian`,
`preprocess`, `sqamt`, or the version-snapshot branches will appear there, even though it may be
exactly the commit that produced the version of the score you're looking at.

To see the full provenance of a score, you need either:

- a local clone (as above, `git log --all --source`), or
- manually switching branches in the GitHub UI (the branch selector dropdown) and repeating the
  same file-history lookup on each branch of interest.

There is no way to get the complete picture from the default GitHub file view alone.
