+++
title = "Strength MCP"
description = "An MCP server for logging and analyzing strength training, backed by a local DuckDB file."
date = "2026-09-17"
author = "Joshua Hull"
techStack = ["Python", "MCP", "DuckDB", "STDIO"]
+++

A Model Context Protocol server that lets me log and review strength training
conversationally. Sessions, sets, RPE, programs, personal records, and analytics all
live in one local DuckDB file, reached through typed tool calls over STDIO.

## Why I rebuilt it

I started from an existing tool whose premise I liked — a single local database
holding exercises, sets, programs, and analytics — but which had a handful of defects
that quietly corrupted data. Rather than patch them, I rebuilt around making each one
structurally impossible:

- **No silent fallbacks.** Resolving an exercise name returns exactly one match or
  raises. There's no default row for a typo to land on.
- **Ambiguity is an error, not a guess.** A short name that matches several exercises
  returns the candidate list instead of picking one arbitrarily.
- **Optional values stay optional.** A missing RPE is handled explicitly by every
  aggregate rather than surfacing as a crash later.
- **Dates are first-class.** Every entry accepts a real date — `2026-08-03`,
  `yesterday`, `3 days ago` — so backdating a session is normal rather than impossible.
- **Derived data stays correct.** Personal records are recomputed on every write, edit,
  and delete.

A rejected write leaves the database completely untouched, and a failed batch reports
*every* bad name at once instead of one per attempt.

## Structure

The domain logic sits apart from the tool surface — separate modules for progression,
personal records, readiness, plate math, and unit handling — so the rules are testable
without going through MCP at all. The tool layer over the top covers workouts,
exercises, programs, analytics, body metrics, and coaching.
