# RunSkeptic Framework Cache

This file records the authoritative Skeptic/RunSkeptic framework HLDspec must use.

## Authoritative source

```text
repository: saffih/skeptic
path: skeptic.md
url: https://github.com/saffih/skeptic/blob/main/skeptic.md
last_verified_sha: 37bbc47ea49ac7ddbfef1bdbfb2bad3fe1ffb5bd
```

## Companion source

```text
repository: saffih/skeptic
path: skeptic-questions.md
url: https://github.com/saffih/skeptic/blob/main/skeptic-questions.md
last_verified_sha: 9740d05a7c2fda9e51443dd03a0aebc79cb861a4
purpose: target-relevant domain question bank
```

## Required phase flow

```text
GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN
```

## Domain question bank

### SEC

SEC1. PII in shared or public files?
SEC2. Subprocess or command from unsanitized user input?
SEC3. File read/written without permission check?
SEC4. Test-data vs real-data boundary enforced?
SEC5. Error messages expose internal paths or stack traces?
SEC6. Authentication check that can be bypassed?
SEC7. Symlinks validated before following?
SEC8. Secrets suppression that can be circumvented?

### CPX

CPX1. Independent concerns tangled in one function?
CPX2. Code that should be data (lookup table, config, enum)?
CPX3. State implicit and scattered vs explicit and managed?
CPX4. Simple (few independent parts), or just familiar?
CPX5. How many things must you hold in your head to understand this?

### REL

REL1. No monitoring - how would you know this is silently broken?
REL2. What fails at 10x scale?
REL3. What external dependency could break this without any code change?
REL4. Bus factor - who knows this, and what if they leave?
REL5. Single source of truth for each important datum?
REL6. Who owns this part or datum, and who is allowed to change it?
REL7. Is ownership/current responsibility clear enough to operate safely?

### DAT

DAT1. Every external call (subprocess, network, DB) timed out?
DAT2. Race condition? Locks minimal and correct?
DAT3. What happens when disk is full or filesystem is read-only?
DAT4. Encoding explicit (UTF-8) or assumed?
DAT5. Where is this data authored?
DAT6. How often is it updated relative to reality?
DAT7. Who consumes it, and is consistency preserved over time?

### ARC

ARC1. Implicit dependency that would surprise a new contributor?
ARC2. Circular dependency between modules?
ARC3. Data flow traceable from input to output?
ARC4. Interfaces/contracts explicit and correct?
ARC5. Relationship exists but is not written down?
ARC6. Connection missing, accidental, or misplaced?

### CFT

CFT1. Test names describe behavior, not implementation?
CFT2. Error message tells you HOW to fix it?
CFT3. Test mocks so much it only tests the mock?

## Domain group parallelization

- SEC+DAT
- CPX+ARC
- REL+CFT

## HLDspec rule

HLDspec may use bounded RunSkeptic review records inside plans and reviews, but those records must identify this cache, preserve the real Skeptic phase flow, and cache the companion domain question bank.

HLDspec must not treat vague `RunSkeptic_cycles` naming as enough evidence that the real framework was used.
