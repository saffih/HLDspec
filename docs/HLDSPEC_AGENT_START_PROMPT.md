# HLDspec Agent Start Prompt

The canonical user-facing prompt is:

```text
HLDspec /absolute/path/to/HLD.md
```

Optional:

```text
HLDspec /absolute/path/to/HLD.md --workspace /path/to/workspace
```

The generated long context is internal. It is not what the human should paste into another agent by default.

The HLDspec-capable agent must expand this trigger by reading the repo contract and generated context files, then using HLDspec tools internally.
