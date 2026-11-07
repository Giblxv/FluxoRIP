#requires -version 5.1
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot '..\tools\printexp_diagnostic\Diagnosticar-PrintExp.ps1')

function Assert-Equal($Actual, $Expected, [string]$Message) {
    if ($Actual -cne $Expected) { throw $Message }
}

Assert-Equal (Get-EndpointKind '127.0.0.1') 'loopback' 'IPv4 loopback'
Assert-Equal (Get-EndpointKind '::1') 'loopback' 'IPv6 loopback'
Assert-Equal (Get-EndpointKind '0.0.0.0') 'any' 'Wildcard IPv4'
Assert-Equal (Get-EndpointKind '::') 'any' 'Wildcard IPv6'
Assert-Equal (Get-EndpointKind '192.0.2.88') 'non_loopback' 'Other address'
Assert-Equal (Get-EndpointKind 'invalid') 'unknown' 'Invalid address'
Assert-Equal (Test-TargetProcess 'App' 'C:\Other\App.exe') $false 'Generic App must be excluded'
Assert-Equal (Test-TargetProcess 'App' 'C:\Program Files\SAi\FlexiPRINT 22\Program\App.exe') $true 'Flexi App'
Assert-Equal (Test-TargetProcess 'PrintExp_X64' 'C:\OperatorPrivate\PrintExp_X64.exe') $true 'PrintExp'
Assert-Equal (Test-TargetProcess 'NWReceive' '') $true 'Receiver without readable path'
Assert-Equal (Test-TargetProcess 'browser' 'C:\Program Files\SAi\browser.exe') $false 'Unrelated process'
$association = ConvertTo-AssociationEvidence '.prt' '"C:\Private Operator\PrintExp_X64.exe" "%1" --private-argument'
Assert-Equal $association.handler 'PrintExp_X64.exe' 'Only executable basename'
Assert-Equal $association.has_file_placeholder $true 'File argument detected without executing'
$associationJson = $association | ConvertTo-Json
if ($associationJson.Contains('Private') -or $associationJson.Contains('private-argument')) { throw 'Association details leaked' }
Assert-Equal (ConvertTo-AssociationEvidence '.prn' 'malformed').state 'unavailable' 'Unsupported command remains unavailable'
Assert-Equal (Get-AccessibilityEvidence ([IntPtr]::Zero)).state 'unavailable' 'No-window accessibility path'

# Fixture functions replace OS enumeration; no software of third parties runs.
function Get-Process {
    @(
        [pscustomobject]@{ ProcessName='PrintExp_X64'; Path='C:\Private\PrintExp_X64.exe'; Id=100; MainModule=[pscustomobject]@{FileVersionInfo=[pscustomobject]@{FileVersion='test-only'}}; MainWindowHandle=[IntPtr]::Zero },
        [pscustomobject]@{ ProcessName='App'; Path='C:\Unrelated\App.exe'; Id=999 },
        [pscustomobject]@{ ProcessName='browser'; Path='C:\Private\browser.exe'; Id=998 }
    )
}
function Get-NetTCPConnection {
    [CmdletBinding()]param()
    @(
        [pscustomobject]@{ OwningProcess=100; State='Listen'; LocalPort=12345; RemotePort=0; LocalAddress='127.0.0.1'; RemoteAddress='0.0.0.0' },
        [pscustomobject]@{ OwningProcess=100; State='Established'; LocalPort=54321; RemotePort=23456; LocalAddress='192.0.2.1'; RemoteAddress='192.0.2.88' },
        [pscustomobject]@{ OwningProcess=999; State='Established'; LocalPort=9999; RemotePort=9998; LocalAddress='198.51.100.1'; RemoteAddress='198.51.100.2' }
    )
}
function Get-OpenAssociation {
    param([string]$Extension)
    [pscustomobject]@{ extension=$Extension; state='unavailable'; handler=$null; has_file_placeholder=$false }
}
$result = Get-StationEvidence -SkipAccessibility -SkipNativeWindows
Assert-Equal $result.processes.Count 1 'Only target processes'
Assert-Equal $result.connections.Count 2 'Only sockets of selected processes'
Assert-Equal $result.tcp_state 'observed' 'TCP collection state'
Assert-Equal $result.mode 'observe_only' 'Read-only mode'
Assert-Equal $result.machine_status 'NAO_VERIFICADO' 'No physical telemetry'
$json = $result | ConvertTo-Json -Depth 12
foreach ($private in @('192.0.2.1','192.0.2.88','198.51.100','C:\Private','Unrelated','browser','MainWindowHandle','CommandLine')) {
    if ($json.Contains($private)) { throw 'Private or unrelated data leaked' }
}

function Get-NetTCPConnection { throw 'Access unavailable' }
$result = Get-StationEvidence -SkipAccessibility -SkipNativeWindows
Assert-Equal $result.tcp_state 'unavailable' 'Permission failure remains partial'
Assert-Equal $result.issues[0] 'tcp_inventory_unavailable' 'Fixed error without system details'

function Get-Process { @() }
function Get-NetTCPConnection { throw 'Must not read table without targets' }
$empty = Get-StationEvidence -SkipAccessibility -SkipNativeWindows
Assert-Equal $empty.processes.Count 0 'No target process'
Assert-Equal $empty.tcp_state 'not_requested_no_target' 'No unnecessary TCP inventory'

$temp = Join-Path ([System.IO.Path]::GetTempPath()) ('fluxo-diag-test-' + [Guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $temp
try {
    $one = Save-StationEvidence $result $temp
    $original = [System.IO.File]::ReadAllText($one)
    $two = Save-StationEvidence $empty $temp
    if ($one -eq $two) { throw 'Report path collision' }
    Assert-Equal ([System.IO.File]::ReadAllText($one)) $original 'Existing report preserved'
    $readback = Get-Content -LiteralPath $two -Raw | ConvertFrom-Json
    Assert-Equal $readback.mode 'observe_only' 'JSON round trip'
    $failed = $false
    try { Save-StationEvidence $empty (Join-Path $temp 'absent') } catch { $failed = $true }
    Assert-Equal $failed $true 'Missing output directory rejected'
} finally { Remove-Item -LiteralPath $temp -Recurse -Force }

# Fail if future code introduces active network/UI actions into the collector.
$source = (Get-ChildItem (Join-Path $PSScriptRoot '..\tools\printexp_diagnostic\*.ps1') | ForEach-Object { Get-Content -LiteralPath $_.FullName -Raw }) -join "`n"
$forbidden = '(?i)Test-NetConnection|Invoke-WebRequest|Invoke-RestMethod|Start-Process|SendKeys|\.Invoke\(|\.SetValue\(|New-Object\s+(?:System\.)?Net\.Sockets|Set-ItemProperty|New-NetFirewallRule|SendMessage|PostMessage|SetWindowLong|GetWindowText|WM_GETTEXT'
if ($source -match $forbidden) { throw 'Unexpected active operation in diagnostic script' }
if ([Environment]::OSVersion.Platform -eq 'Win32NT') {
    $native = Get-Win32WindowEvidence -TargetProcessId $PID
    Assert-Equal $native.state 'observed' 'Actual Win32 metadata enumeration'
    foreach ($node in $native.nodes) {
        foreach ($key in @('node_id','parent_node_id','control_id','class_name','top_level','visible','enabled','style')) {
            if ($key -notin @($node.PSObject.Properties.Name)) { throw 'Missing native metadata field' }
        }
        if ($node.PSObject.Properties.Name -match '^(handle|title|text|value|name)$') { throw 'Window contents or handles leaked' }
    }
    if ($PSVersionTable.PSEdition -eq 'Desktop') {
        Add-Type -AssemblyName System.Windows.Forms
        $form = New-Object System.Windows.Forms.Form
        try {
            $form.Text = 'PRIVATE_ARTWORK_TITLE'
            $button = New-Object System.Windows.Forms.Button
            $button.Text = 'PRIVATE_JOB_BUTTON'
            $button.Name = 'PRIVATE_JOB_AUTOMATION_ID'
            $form.Controls.Add($button)
            $form.Show()
            [System.Windows.Forms.Application]::DoEvents()
            $fixture = Get-Win32WindowEvidence -TargetProcessId $PID
            Assert-Equal $fixture.state 'observed' 'Win32 fixture collection'
            if (@($fixture.nodes | Where-Object { $_.top_level }).Count -lt 1) { throw 'Fixture root missing' }
            if (@($fixture.nodes | Where-Object { $_.class_name -match 'BUTTON' -and $null -ne $_.parent_node_id }).Count -lt 1) { throw 'Fixture button metadata missing' }
            if (($fixture | ConvertTo-Json -Depth 6).Contains('PRIVATE_')) { throw 'Fixture title, label or automation name leaked' }
        } finally { $form.Dispose() }
    }
} else {
    Assert-Equal (Get-Win32WindowEvidence -TargetProcessId 1).state 'unavailable' 'Non-Windows fallback'
}
Write-Host 'PASS: endpoint redaction, target filtering, partial errors, no-target path, report preservation, JSON and read-only contract.'
