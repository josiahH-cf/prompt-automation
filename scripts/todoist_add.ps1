param(
  [Parameter(Mandatory=$false, Position=0)] [string] $Summary,
  [Parameter(Mandatory=$false, Position=1)] [string] $Note,
  [switch] $DryRun
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host "[INFO] $msg" }
function Write-Warn($msg) { Write-Host "[WARN] $msg" }
function Write-Err($msg)  { Write-Error "[ERROR] $msg" }

function Get-RepoRoot {
  # Assume script lives under <repo>\scripts\todoist_add.ps1
  $here = Split-Path -Parent $PSCommandPath
  $candidate = Split-Path -Parent $here
  # Heuristic: repo root contains either pyproject.toml or espanso-package
  if (Test-Path (Join-Path $candidate 'pyproject.toml') -PathType Leaf) { return $candidate }
  if (Test-Path (Join-Path $candidate 'espanso-package') -PathType Container) { return $candidate }
  # Try one level higher as a fallback
  $up = Split-Path -Parent $candidate
  if ($up -and (Test-Path (Join-Path $up 'espanso-package') -PathType Container)) { return $up }
  return $candidate
}

function Load-TodoistToken {
  param(
    [Parameter(Mandatory=$true)][string] $RepoRoot
  )
  # 1) Env var takes precedence. Allow override of var name via TODOIST_TOKEN_ENV, default to TODOIST_API_TOKEN
  $varName = 'TODOIST_API_TOKEN'
  if ($env:TODOIST_TOKEN_ENV) { $varName = $env:TODOIST_TOKEN_ENV }
  $tok = [Environment]::GetEnvironmentVariable($varName, 'Process')
  if (-not $tok) { $tok = [Environment]::GetEnvironmentVariable($varName, 'User') }
  if (-not $tok) { $tok = [Environment]::GetEnvironmentVariable($varName, 'Machine') }
  if ($tok) { return @{ token = $tok; source = "env:$varName" } }

  # 2) Repo-local secret file (gitignored):
  #    - Default: local.secrets.psd1 (back-compat for tests and existing setups)
  #    - Opt-in: local.secrets.todoist.psd1 when TODOIST_USE_TODOIST_FILE=1|true|yes
  $useNew = ($env:TODOIST_USE_TODOIST_FILE -and ($env:TODOIST_USE_TODOIST_FILE -match '^(1|true|yes)$'))
  $secretsOld = Join-Path $RepoRoot 'local.secrets.psd1'
  $secretsNew = Join-Path $RepoRoot 'local.secrets.todoist.psd1'
  $secretsPath = ''
  if ($useNew -and (Test-Path $secretsNew -PathType Leaf)) { $secretsPath = $secretsNew }
  elseif (Test-Path $secretsOld -PathType Leaf) { $secretsPath = $secretsOld }
  if ($secretsPath -and (Test-Path $secretsPath -PathType Leaf)) {
    try {
      $data = Import-PowerShellDataFile -Path $secretsPath
    } catch {
      throw "Failed to read secrets from $secretsPath. Error: $($_.Exception.Message)"
    }
    if ($null -ne $data -and $data.ContainsKey('TODOIST_API_TOKEN') -and $data.TODOIST_API_TOKEN) {
      return @{ token = [string]$data.TODOIST_API_TOKEN; source = "file:$([IO.Path]::GetFileName($secretsPath))" }
    }
    if ($data -and $data.ContainsKey('TODOIST_TOKEN') -and $data.TODOIST_TOKEN) {
      return @{ token = [string]$data.TODOIST_TOKEN; source = "file:$([IO.Path]::GetFileName($secretsPath))" }
    }
    throw "Secret file present but missing TODOIST_API_TOKEN key"
  }

  throw 'Todoist token not found. Set env TODOIST_API_TOKEN or create local.secrets.psd1 with @{ TODOIST_API_TOKEN = ''<YOUR_TOKEN>'' }'
}

function Parse-Inputs {
  param(
    [string] $SummaryArg,
    [string] $NoteArg
  )
  $summary = ($SummaryArg | ForEach-Object { $_ })
  if (-not $summary) { $summary = '' }
  $summary = $summary.Trim()
  if (-not $summary) {
    throw 'Action text is required. Got empty summary string.'
  }

  # Description: prefer value after 'NRA: ' prefix in note if present, else use note as-is
  $desc = ''
  if ($NoteArg) {
    $desc = [regex]::Replace($NoteArg, '^\s*NRA:\s*', '')
    $desc = $desc.Trim()
  }

  # Derive minimal content: try to extract the 'action' part from patterns like "TYPE - action — DoD: ..."
  $content = $summary
  try {
    # Split on em dash or hyphen patterns to find a segment that looks like the action
    $candidate = $summary
  if ($summary -match '\s—\s') { $candidate = $summary.Split('—')[0] }
  if ($candidate -match '\s-\s') { $candidate = ($candidate.Split('-') | Select-Object -Last 1) }
    $candidate = $candidate.Trim()
    if ($candidate) { $content = $candidate }
  } catch { }

  return @{ content = $content; description = $desc; rawSummary = $summary; rawNote = $NoteArg }
}

if ($env:NTSK_DISABLE -and ($env:NTSK_DISABLE -match '^(1|true|yes)$')) {
  Write-Warn "NTSK disabled via NTSK_DISABLE env var. No-op."
  exit 0
}

try {
  $repoRoot = Get-RepoRoot
  $inputs   = Parse-Inputs -SummaryArg $Summary -NoteArg $Note
  $tokenObj = $null
  try {
    $tokenObj = Load-TodoistToken -RepoRoot $repoRoot
  } catch {
  throw
  }

  $payload = @{ content = $inputs.content }
  if ($inputs.description) { $payload.description = $inputs.description }

  if ($DryRun -or ($env:TODOIST_DRY_RUN -as [int])) {
    Write-Info ("DRY RUN -> Would create Todoist task | content='{0}'{1} | tokenSource={2}" -f `
      $payload.content, `
      ($payload.ContainsKey('description') ? ("; description='" + $payload.description + "'") : ''), `
      $tokenObj.source)
    exit 0
  }

  # Real request
  $headers = @{ Authorization = ("Bearer {0}" -f $tokenObj.token) }
  $uri = 'https://api.todoist.com/rest/v2/tasks'
  $body = $payload | ConvertTo-Json -Depth 5
  $resp = Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -Body $body -ContentType 'application/json'
  $id = $resp.id
  if ($id) {
    Write-Info ("Created Todoist task id={0} content='{1}'" -f $id, $payload.content)
  } else {
    Write-Info ("Created Todoist task | content='{0}'" -f $payload.content)
  }
  exit 0
} catch {
  Write-Err $_.Exception.Message
  exit 1
}

