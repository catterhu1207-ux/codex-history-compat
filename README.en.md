# codex-history-compat

An experimental patch for OpenAI Codex commit `b5bffd3ec4db487e7e3dec59663875b0ef7b72ca`. It normalizes outbound prompt copies for Responses-compatible providers while leaving durable history untouched. Apply with `apply.ps1` or `apply.sh`, then run the focused `codex-core` tests documented in the Chinese README.

Related projects: [electron-update-safety](https://github.com/catterhu1207-ux/electron-update-safety) and [desktop-adaptation-lab](https://github.com/catterhu1207-ux/desktop-adaptation-lab).
