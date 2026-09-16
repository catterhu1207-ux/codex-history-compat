# v0.1.0

Experimental patch release targeting OpenAI Codex commit `b5bffd3ec4db487e7e3dec59663875b0ef7b72ca`.

- Normalizes only the outbound request copy; persistent history remains unchanged.
- Integrates the same compatibility pass into ordinary Responses requests, WebSocket requests, local compaction, and both remote compaction paths.
- Preserves valid tool-call ordering and pairing while handling encrypted reasoning and misplaced notice messages.
- Includes reproducible apply scripts and a synthetic regression fixture.

Remote-provider tests are outside the default CI contract.
