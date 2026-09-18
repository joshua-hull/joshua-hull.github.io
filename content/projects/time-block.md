+++
title = "Time Block"
description = "A local-first planner that auto-allocates your work week across projects."
date = "2026-07-17"
author = "Joshua Hull"
techStack = ["Next.js 16", "React 19", "TypeScript", "Prisma 7", "SQLite", "Tailwind CSS v4", "dnd-kit", "Vitest"]
+++

A single-user web app for time-blocking a work week. You define projects and the
percentage of each work day they should get, add meetings and personal blocks that
don't count toward project hours, and the app fills in the rest.

## The allocation engine

The piece I care most about. For each work day it starts from your configured hours,
subtracts meetings and personal time, then water-fills the remainder with project
blocks proportional to each project's target percentage — spread across the week so
the *weekly* totals converge on target rather than forcing every day to match.

It's a pure function with no knowledge of the UI, which means it's unit-tested
directly instead of through the interface. Dragging a block adjusts it and locks it,
and re-allocation then routes around the locked block instead of overwriting it.

## Other pieces worth noting

- **Recurring templates that split cleanly.** Editing a single occurrence leaves the
  template alone; a "this and all future" edit splits the template at a week boundary
  rather than rewriting history.
- **Per-week target overrides**, so one unusual week doesn't require changing a
  project's standing target.
- **Read-only past weeks**, a configurable work week, and per-day available hours.

Built with the App Router on a local SQLite file via Prisma's `better-sqlite3` driver
adapter — no auth, no server, no account. It runs on my machine and nowhere else.
Later work migrated the whole interface onto shadcn/ui, and the visual language
that came out of it is the same one this site is built on.
