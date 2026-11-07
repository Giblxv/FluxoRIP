#requires -version 5.1
param([string]$FixtureExe)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '..\tools\printexp_prepare\Preparar-Caminho.ps1')
. (Join-Path $PSScriptRoot '..\tools\printexp_diagnostic\Read-Win32Controls.ps1')
Initialize-FileDialogGuard

function Assert-Equal($Actual, $Expected, [string]$Message) {
    if ($Actual -cne $Expected) { throw $Message }
}
Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::IsOpenRole('&Open')) $true 'Open label'
Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::IsOpenRole('&Abrir')) $true 'Portuguese open label'
Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::IsOpenRole('&Save')) $false 'Save must not match'
Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::IsOpenRole('Imprimir')) $false 'Print must not match'
Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::IsCancelRole('Cancelar')) $true 'Portuguese cancellation'
Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::IsCancelRole('Confirmar')) $false 'Unexpected cancellation role'
foreach ($path in @('C:\synthetic\art.PRT','D:\art with spaces.prn')) {
    Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::IsSafePathSyntax($path)) $true 'Supported path syntax'
}
foreach ($path in @('relative.prt','\\host\share\a.prt','C:\a.txt','C:\a.prt:stream.prt',"C:\a`n.prt",'C:\"a.prt"','C:\*.prt','C:\CON.prt','C:\folder\LPT1.prn',('C:\' + ('x' * 260) + '.prt'))) {
    Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::IsSafePathSyntax($path)) $false 'Unsafe or unsupported path rejected'
}
Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Prepare('invalid','C:\synthetic\a.prt').State) 'token_invalid' 'No uninspected write'
$baseReport = New-PreparationReport
Assert-Equal $baseReport.mode 'inspect_only' 'Inspection default'
Assert-Equal $baseReport.helper_confirmed_file $false 'No file confirmation claim'
Assert-Equal $baseReport.helper_requested_print $false 'No print request claim'
Assert-Equal $baseReport.machine_status 'NAO_VERIFICADO' 'No physical telemetry'
function Get-Process { @() }
Assert-Equal (Get-PreparationTarget).state 'expected_one_printexp_process' 'No target remains inactive'
function Get-Process {
    @([pscustomobject]@{ProcessName='PrintExp_X64';Id=10},[pscustomobject]@{ProcessName='PrintExp_Second';Id=11})
}
Assert-Equal (Get-PreparationTarget).state 'expected_one_printexp_process' 'Multiple targets rejected'

$source = (Get-ChildItem (Join-Path $PSScriptRoot '..\tools\printexp_prepare\*') -Include '*.ps1','*.cs' -File | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw }) -join "`n"
$forbidden = '(?i)WM_COMMAND|BM_CLICK|SendKeys|SendInput|PostMessage|ShellExecute|Start-Process|Test-NetConnection|Invoke-WebRequest|Invoke-RestMethod|TcpClient|System\.Net\.Sockets'
if ($source -match $forbidden) { throw 'Unexpected confirmation, process launch or network operation' }
$writes = [regex]::Matches($source,'WriteText\(expected\.Edit, WriteMessage,')
Assert-Equal $writes.Count 1 'One narrowly scoped path write site'

if ([Environment]::OSVersion.Platform -eq 'Win32NT' -and $FixtureExe) {
    $temp = Join-Path ([System.IO.Path]::GetTempPath()) ('fluxo-prepare-test-' + [Guid]::NewGuid().ToString('N'))
    $null = New-Item -ItemType Directory -Path $temp
    $sample = Join-Path $temp ('synthetic ' + [char]0x00E7 + [char]0x00E3 + 'o.prt')
    [System.IO.File]::WriteAllText($sample, 'synthetic data - not a printable file')
    $before = (Get-FileHash -LiteralPath $sample -Algorithm SHA256).Hash
    function Start-Fixture([string]$Kind) {
        $arguments = @(('"' + $temp + '"'), $Kind)
        $process = Start-Process -FilePath $FixtureExe -ArgumentList $arguments -PassThru
        for ($attempt = 0; $attempt -lt 80; $attempt++) {
            if ($process.HasExited) { throw 'Fixture exited' }
            $view = [FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Inspect($process.Id)
            if (($Kind -eq 'open' -and $view.CanPrepare) -or ($Kind -eq 'nonempty' -and $view.State -eq 'input_not_empty')) { return $process }
            if ($Kind -eq 'save') {
                $native = Get-Win32WindowEvidence -TargetProcessId $process.Id
                $byId = @{}
                foreach ($node in $native.nodes) { $byId[$node.node_id] = $node }
                foreach ($node in $native.nodes) {
                    if ($node.top_level -and $node.visible -and $node.enabled -and $node.class_name -eq '#32770' -and $null -ne $node.parent_node_id -and $byId.ContainsKey($node.parent_node_id) -and -not $byId[$node.parent_node_id].enabled) { return $process }
                }
            }
            Start-Sleep -Milliseconds 100
        }
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        throw 'Synthetic Open dialog did not meet the supported guard'
    }
    try {
        $fixture = Start-Fixture 'open'
        try {
            $inspection = [FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Inspect($fixture.Id)
            Assert-Equal $inspection.CanPrepare $true 'Actual standard Open dialog recognized'
            $missing = [FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Prepare($inspection.Token,(Join-Path $temp 'missing.prt'))
            Assert-Equal $missing.State 'file_missing' 'Missing input rejected before UI write'
            Assert-Equal $missing.WriteAttempted $false 'No write for missing input'
            $inspection = [FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Inspect($fixture.Id)
            $outcome = [FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Prepare($inspection.Token,$sample)
            Assert-Equal $outcome.State 'path_prepared_confirmation_manual' 'Only path prepared'
            Assert-Equal $outcome.PathVerified $true 'Text readback matches selected path'
            Assert-Equal $outcome.DialogStillOpen $true 'Dialog remains open'
            Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Prepare($inspection.Token,$sample).State) 'token_invalid' 'No automatic retry or token reuse'
            Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Inspect($fixture.Id).State) 'input_not_empty' 'Existing field preserved'
            if (Test-Path (Join-Path $temp 'confirmation-was-triggered.txt')) { throw 'File confirmation was triggered' }
        } finally { Stop-Process -Id $fixture.Id -Force -ErrorAction SilentlyContinue }
        $fixture = Start-Fixture 'nonempty'
        try {
            Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Inspect($fixture.Id).CanPrepare) $false 'Operator draft never overwritten'
        } finally { Stop-Process -Id $fixture.Id -Force -ErrorAction SilentlyContinue }
        $fixture = Start-Fixture 'save'
        try {
            Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Inspect($fixture.Id).CanPrepare) $false 'Save dialog rejected'
        } finally { Stop-Process -Id $fixture.Id -Force -ErrorAction SilentlyContinue }
        $fixture = Start-Fixture 'open'
        $stale = [FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Inspect($fixture.Id)
        Stop-Process -Id $fixture.Id -Force
        $outcome = [FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Prepare($stale.Token,$sample)
        Assert-Equal $outcome.WriteAttempted $false 'Closed dialog never receives a path'
        Assert-Equal ((Get-FileHash -LiteralPath $sample -Algorithm SHA256).Hash) $before 'Original file unchanged'
    } finally { Remove-Item -LiteralPath $temp -Recurse -Force }
} elseif ([Environment]::OSVersion.Platform -ne 'Win32NT') {
    Assert-Equal ([FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Inspect(1).State) 'windows_required' 'Non-Windows remains inactive'
}
Write-Host 'PASS: role guards, path policy, explicit preparation, no confirmation, no printing, synthetic Windows dialogs when available.'
