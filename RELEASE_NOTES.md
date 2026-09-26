# v0.2.0

Add a separately pinned `0.158.0-alpha.2` backend profile for Codex Desktop `26.924.1866.0`, with optional Windows source-build tooling, migration-byte checks and build provenance. Preserve the legacy patch and apply interfaces.

The new profile preserves tool metadata while normalizing outbound history across ordinary requests, WebSocket, local compaction and remote compaction V2. Durable history is unchanged. Fixtures are synthetic; compiled backends and official desktop binaries are not distributed.

# v0.1.0

Experimental patch release targeting OpenAI Codex commit `b5bffd3ec4db487e7e3dec59663875b0ef7b72ca`.

- Normalizes only the outbound request copy; persistent history remains unchanged.
- Integrates the same compatibility pass into ordinary Responses requests, WebSocket requests, local compaction, and both remote compaction paths.
- Preserves valid tool-call ordering and pairing while handling encrypted reasoning and misplaced notice messages.
- Includes reproducible apply scripts and a synthetic regression fixture.

Remote-provider tests are outside the default CI contract.
