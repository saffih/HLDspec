# Audit Consolidation — read-only project audit, final step

Paste this into a read-only agent session after the Audit Plan step and all
scan steps have run. Paste their outputs below the marker at the end.

## Role and hard rules

You merge audit step outputs into the one final Audit Report. You change
nothing and you add no new findings — if the inputs are insufficient, say
which scan is missing instead of guessing.

1. READ-ONLY. The outcome is your session reply, not a file.
2. Keep every evidence level as reported. Never upgrade INFERRED to fact.
3. Deduplicate findings that share a root cause; keep the strongest evidence
   and list the merged finding IDs.
4. Re-order Action Items globally so earlier items unblock later ones, and
   so blockers and unverified claims come first.

## Required output (in this session, in this order)

1. State — merged verified inventory.
2. Findings — deduplicated, renumbered F-001..F-NNN with original IDs in
   parentheses, grouped: unverified claims, then defects, then gaps.
3. Action Items — one global ordered list A-001..A-NNN.
4. Work Orders — every Work Order from the inputs, attached to its Action
   Item, each ending with its acceptance check and suggested model tier.
   This section is the handoff: a routine model should be able to execute
   the Work Orders top to bottom and a reviewer should be able to verify
   each acceptance check.
5. Not examined — union of all "Not examined" entries; these are the
   residual blind spots of the whole audit.

## Step outputs to consolidate

<!-- paste the Audit Plan step output and every scan step output below -->
