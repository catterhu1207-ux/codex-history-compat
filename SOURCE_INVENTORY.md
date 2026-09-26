# Source and license inventory

| Path | Origin | License basis |
|---|---|---|
| `patches/integration.patch` | Minimal diff against `openai/codex` commit `b5bffd3ec4db487e7e3dec59663875b0ef7b72ca` | Apache-2.0 upstream source; LICENSE and NOTICE retained |
| `patches/prompt_history_compat.rs` | Compatibility module developed for this patch, using upstream Codex types | Apache-2.0 for compatibility with the patched work |
| `patches/deepseek_notice_batch.json` | Synthetic regression fixture | Apache-2.0 project license |
| `apply.ps1`, `apply.sh`, docs and CI | Original release tooling and documentation | Apache-2.0 project license |

The repository excludes compiled binaries, official desktop packages, authentic requests, conversation identifiers, user paths, databases, and logs.

## 0.158.0-alpha.2 additions

`profiles/0.158.0-alpha.2/integration.patch` is a minimal Apache-2.0 upstream diff against commit `10382da79a2a2d6e8ae221fa63077215389c1ad2`. The compatibility module and synthetic fixture retain the project Apache-2.0 license. Profile and migration files contain public source identities only. `build_backend.py` and packaging tests are original release tooling. No private maintenance directory, real request, task record or compiled executable is included.

## Desktop 26.924.2738.0

`profiles/desktop-26.924.2738.0` pins upstream `0d9c7cbfa6cf1489f55a8a9542b75ddd2c061807` and retains the Apache-2.0 module, minimal integration patch and synthetic fixture. The upstream compatibility integration files and migration tree are unchanged from the prior pinned revision. [Source evidence](SOURCE_26.924.2738.0.json) records the official package and upstream release identity checks.
