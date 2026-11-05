# GitHub Actions Windows smoke test: synthetic inputs, no vendor PRT bytes.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:RUNNER_TEMP ("autorip-smoke-" + [Guid]::NewGuid().ToString('N'))
$sampleDir = Join-Path $root 'samples'
try {
    New-Item -ItemType Directory -Path $sampleDir -Force | Out-Null
    $common = Join-Path $root 'common-settings.txt'
    [IO.File]::WriteAllText($common, 'SYNTHETIC-only: locked RIP configuration')
    $arts = @{}
    foreach ($art in @('art_a', 'art_b', 'art_c')) {
        $artPath = Join-Path $root ($art + '.txt')
        [IO.File]::WriteAllText($artPath, 'SYNTHETIC artwork source: ' + $art)
        $arts[$art] = $artPath
        foreach ($level in @('white_0', 'white_50', 'white_100')) {
            $repeats = if ($level -eq 'white_50') { @(1,2) } else { @(1) }
            foreach ($r in $repeats) {
                $filename = $art + '_' + $level + '_r' + $r + '.PRT'
                $payload = ('SYNTHETIC:' + $art + '/' + $level + ';') * 8
                [IO.File]::WriteAllBytes((Join-Path $sampleDir $filename),
                    [Text.Encoding]::ASCII.GetBytes($payload))
            }
        }
    }
    $template = Join-Path $root 'template.json'
    $filled = Join-Path $root 'filled.json'
    $report = Join-Path $root 'verified.json'
    & python (Join-Path $PSScriptRoot 'controlled_capture.py') template --experiment-id 'CI_synthetic_001' --output $template
    if ($LASTEXITCODE -ne 0) { throw 'Python template creation failed' }

    $params = @{
        Template = $template
        SampleDirectory = $sampleDir
        ArtworkA = $arts['art_a']
        ArtworkB = $arts['art_b']
        ArtworkC = $arts['art_c']
        CommonConfig = $common
        Output = $filled
    }
    & (Join-Path $PSScriptRoot 'fill_capture_manifest.ps1') @params

    & python (Join-Path $PSScriptRoot 'controlled_capture.py') verify --manifest $filled --directory $sampleDir --output $report
    if ($LASTEXITCODE -ne 0) { throw 'Independent Python SHA-256 validation failed' }
    $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
    if ($result.verified_file_count -ne 12 -or @($result.warnings).Count -ne 0) {
        throw 'Unexpected synthetic experiment report'
    }
    $existingResult = Get-Content -LiteralPath $filled -Raw
    try {
        & (Join-Path $PSScriptRoot 'fill_capture_manifest.ps1') @params
        throw 'Expected refusal to overwrite existing manifest'
    }
    catch {
        if ($_.Exception.Message -eq 'Expected refusal to overwrite existing manifest') {
            throw
        }
    }
    if ((Get-Content -LiteralPath $filled -Raw) -ne $existingResult) {
        throw 'Existing manifest contents were modified'
    }
    Write-Host 'PASS: Get-FileHash then Python SHA-256 verified 12 synthetic captures; no overwrite'
}
finally {
    if (Test-Path -LiteralPath $root) {
        Remove-Item -LiteralPath $root -Recurse -Force
    }
}
