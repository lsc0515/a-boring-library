param(
  [string]$Target = 'both'
)

$ErrorActionPreference = 'Stop'

$repoRoot = $PSScriptRoot
if (-not $repoRoot) {
  $repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}

$bashCandidates = @(
  'C:\Program Files\Git\bin\bash.exe',
  'C:\Program Files\Git\usr\bin\bash.exe',
  'bash'
)

$bash = $null
foreach ($candidate in $bashCandidates) {
  if (Get-Command $candidate -ErrorAction SilentlyContinue) {
    $bash = (Get-Command $candidate).Source
    break
  }
}

if (-not $bash) {
  throw 'Git Bash not found. Install Git for Windows or run skills.sh from bash.'
}

& $bash "$repoRoot/skills.sh" $Target
