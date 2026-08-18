# Skill Observation Log

Observations captured during task-oriented work.

**Status key:** OPEN = not yet actioned | ACTIONED (YYYY-MM-DD) = skill
updated/created | DECLINED (YYYY-MM-DD) = user decided not to pursue —
resolved statuses always carry their resolution date

---

## 2026-08-16

### Observation 1: Parallel program JSON needs an explicit gitignore exception

**Status:** OPEN
**Date:** 2026-08-16
**Session context:** Version 2A phase A0 architecture freeze on ComicMainEngine
**Skill:** New skill candidate: parallel-track program freeze
**Type:** open-source
**Phase/Area:** session start / repo hygiene

**Issue:** The repo gitignores `data/*` with a short allowlist. A new first-class program file (`data/v2a_program.json`) would be silently untracked unless `!data/v2a_program.json` is added next to the existing exceptions. The architecture doc alone is not enough for a readable-without-code gate if the program JSON never lands in git.

**Suggested improvement:** When freezing a parallel track, treat the gitignore allowlist as part of the freeze checklist: new tracked JSON under an ignored directory needs an explicit exception in the same commit as the file.

**Principle:** If a directory is gitignored by default, a new source-of-truth file in that directory is not done until the ignore exception and the file ship together.
