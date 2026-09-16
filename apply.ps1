[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$CodexRoot)
$ErrorActionPreference='Stop'
$expected='b5bffd3ec4db487e7e3dec59663875b0ef7b72ca'
$root=[IO.Path]::GetFullPath($CodexRoot)
$actual=(git -C $root rev-parse HEAD).Trim()
if($LASTEXITCODE -ne 0 -or $actual -ne $expected){throw "Expected upstream commit $expected; found $actual"}
if(git -C $root status --porcelain){throw 'The upstream working tree must be clean.'}
$here=Split-Path -Parent $MyInvocation.MyCommand.Path
git -C $root apply --check (Join-Path $here 'patches\integration.patch')
if($LASTEXITCODE -ne 0){throw 'Integration patch does not apply cleanly.'}
git -C $root apply (Join-Path $here 'patches\integration.patch')
Copy-Item -LiteralPath (Join-Path $here 'patches\prompt_history_compat.rs') -Destination (Join-Path $root 'codex-rs\core\src\prompt_history_compat.rs')
$fixtureDir=Join-Path $root 'codex-rs\core\src\prompt_history_compat_fixtures'
New-Item -ItemType Directory -Path $fixtureDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $here 'patches\deepseek_notice_batch.json') -Destination (Join-Path $fixtureDir 'deepseek_notice_batch.json')
Write-Host 'Patch applied. Run: cargo test --manifest-path codex-rs/Cargo.toml -p codex-core prompt_history_compat --lib -- --test-threads 1'
