#!/usr/bin/env bash
set -euo pipefail
root="${1:?usage: ./apply.sh /path/to/openai-codex}"
expected=b5bffd3ec4db487e7e3dec59663875b0ef7b72ca
actual="$(git -C "$root" rev-parse HEAD)"
test "$actual" = "$expected" || { echo "Expected $expected; found $actual" >&2; exit 2; }
test -z "$(git -C "$root" status --porcelain)" || { echo "Upstream tree must be clean" >&2; exit 2; }
here="$(cd "$(dirname "$0")" && pwd)"
git -C "$root" apply --check "$here/patches/integration.patch"
git -C "$root" apply "$here/patches/integration.patch"
cp "$here/patches/prompt_history_compat.rs" "$root/codex-rs/core/src/prompt_history_compat.rs"
mkdir -p "$root/codex-rs/core/src/prompt_history_compat_fixtures"
cp "$here/patches/deepseek_notice_batch.json" "$root/codex-rs/core/src/prompt_history_compat_fixtures/deepseek_notice_batch.json"
echo 'Patch applied. Run cargo test --manifest-path codex-rs/Cargo.toml -p codex-core prompt_history_compat --lib -- --test-threads 1'
