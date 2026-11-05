<#
.SYNOPSIS
  Fill an AutoRIP controlled-capture template with independent Windows
  Get-FileHash SHA-256 values. No PRT modification, printer access or license work.
.DESCRIPTION
  This is operator-side attestation, not a vendor certification. Python's
  controlled_capture.py independently rehashes every PRT before reporting.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Template,
    [Parameter(Mandatory=$true)][string]$SampleDirectory,
    [Parameter(Mandatory=$true)][string]$ArtworkA,
    [Parameter(Mandatory=$true)][string]$ArtworkB,
    [Parameter(Mandatory=$true)][string]$ArtworkC,
    [Parameter(Mandatory=$true)][string]$CommonConfig,
    [Parameter(Mandatory=$true)][string]$Output
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-Sha256Lower([string]$Path) {
    $item = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($item.PSIsContainer) { throw "Expected a regular file, got directory: $Path" }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "Symbolic/reparse-point input refused: $Path"
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
}

if (!(Test-Path -LiteralPath $SampleDirectory -PathType Container)) {
    throw "SampleDirectory must be an existing directory"
}
$plan = Get-Content -LiteralPath $Template -Raw -Encoding UTF8 | ConvertFrom-Json
if ($plan.schema -ne 'autorip-controlled-capture-v1') {
    throw "Unexpected capture-plan schema"
}
if (@($plan.samples).Count -ne 12) {
    throw "Expected exactly 12 controlled samples"
}

$plan.common_config_sha256 = Get-Sha256Lower $CommonConfig
$plan.artworks.art_a = Get-Sha256Lower $ArtworkA
$plan.artworks.art_b = Get-Sha256Lower $ArtworkB
$plan.artworks.art_c = Get-Sha256Lower $ArtworkC

foreach ($record in $plan.samples) {
    $filename = [string]$record.filename
    if ($filename -cnotmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.[Pp][Rr][Tt]$') {
        throw "Unsafe filename in plan; only a plain .PRT basename is accepted"
    }
    $samplePath = Join-Path $SampleDirectory $filename
    $info = Get-Item -LiteralPath $samplePath -ErrorAction Stop
    if ($info.PSIsContainer -or (($info.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
        throw "Sample must be a regular, non-symlink file: $filename"
    }
    if ($info.Length -lt 48) {
        throw "Sample PRT is unexpectedly short: $filename"
    }
    # The independent Python verification pass checks both length and digest.
    $record.size_bytes = [long]$info.Length
    $record.sha256 = Get-Sha256Lower $samplePath
}

$json = $plan | ConvertTo-Json -Depth 10
$stream = [IO.File]::Open($Output, [IO.FileMode]::CreateNew,
                         [IO.FileAccess]::Write, [IO.FileShare]::None)
try {
    $writer = New-Object System.IO.StreamWriter($stream, (New-Object System.Text.UTF8Encoding($false)))
    try {
        $writer.Write($json)
        $writer.Write([Environment]::NewLine)
        $writer.Flush()
    }
    finally {
        $writer.Dispose()
    }
}
finally {
    $stream.Dispose()
}
Write-Host "Filled a new operator-side SHA-256 manifest: $Output"
Write-Host "Next: python controlled_capture.py verify --manifest ... --directory ... --output ..."
