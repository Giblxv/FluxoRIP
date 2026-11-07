#requires -version 5.1
<## Read-only station inventory. No printer communication or UI actions. ##>
[CmdletBinding()]
param(
    [string]$OutputDirectory,
    [switch]$SkipAccessibility,
    [switch]$SkipNativeWindows,
    [switch]$NonInteractive
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Read-Win32Controls.ps1')

function Get-EndpointKind {
    param([string]$Address)
    $parsed = $null
    if (-not [System.Net.IPAddress]::TryParse($Address, [ref]$parsed)) { return 'unknown' }
    if ([System.Net.IPAddress]::IsLoopback($parsed)) { return 'loopback' }
    if ($parsed.Equals([System.Net.IPAddress]::Any) -or $parsed.Equals([System.Net.IPAddress]::IPv6Any)) { return 'any' }
    return 'non_loopback'
}

function Test-TargetProcess {
    param([string]$Name, [string]$ExecutablePath)
    if ($Name -match '^(PrintExp(?:[_-].*)?|NWReceive)$') { return $true }
    # App.exe/App2.exe are generic names. Require the publisher's installation path.
    if ($Name -match '^(App2?|Production Manager|ProductionManager|FlexiPRINT|FlexiSign(?:Pro)?)$') {
        return [bool]($ExecutablePath -match '(?i)[\\/](SAi|Flexi[^\\/]*|Production Manager)[\\/]')
    }
    return $false
}

function ConvertTo-AssociationEvidence {
    param([string]$Extension, [string]$Command)
    $result = [ordered]@{ extension = $Extension; state = 'unavailable'; handler = $null; has_file_placeholder = $false }
    # Parse metadata only; never execute or export command, arguments or paths.
    $match = [regex]::Match($Command, '^\s*(?:"(?<exe>[^"]+\.exe)"|(?<exe>[^\s"]+\.exe))', 'IgnoreCase')
    if ($match.Success) {
        $result.handler = [System.IO.Path]::GetFileName($match.Groups['exe'].Value.Replace('\', '/'))
        $result.has_file_placeholder = [bool]($Command -match '(?i)%[1l]')
        $result.state = 'observed'
    }
    return [pscustomobject]$result
}

function Get-OpenAssociation {
    param([ValidateSet('.prt', '.prn')][string]$Extension)
    $result = [ordered]@{ extension = $Extension; state = 'unavailable'; handler = $null; has_file_placeholder = $false }
    try {
        $choice = Get-ItemProperty -LiteralPath "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\$Extension\UserChoice" -Name ProgId -ErrorAction SilentlyContinue
        $programId = $null
        if ($choice) { $programId = $choice.ProgId }
        if (-not $programId) {
            $key = Get-Item -LiteralPath "Registry::HKEY_CLASSES_ROOT\$Extension" -ErrorAction Stop
            $programId = $key.GetValue('')
        }
        if (-not $programId) { return [pscustomobject]$result }
        $commandKey = Get-Item -LiteralPath "Registry::HKEY_CLASSES_ROOT\$programId\shell\open\command" -ErrorAction Stop
        $command = [string]$commandKey.GetValue('')
        return ConvertTo-AssociationEvidence $Extension $command
    } catch { }
    return [pscustomobject]$result
}

function Get-AccessibilityEvidence {
    param([IntPtr]$WindowHandle)
    $result = [ordered]@{ state = 'unavailable'; nodes = @(); truncated = $false }
    if ($WindowHandle -eq [IntPtr]::Zero) { return [pscustomobject]$result }
    try {
        Add-Type -AssemblyName UIAutomationClient
        Add-Type -AssemblyName UIAutomationTypes
        $root = [System.Windows.Automation.AutomationElement]::FromHandle($WindowHandle)
        $queue = New-Object System.Collections.Queue
        $queue.Enqueue(@{ element = $root; depth = 0 })
        $nodes = New-Object 'System.Collections.Generic.List[object]'
        $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
        while ($queue.Count -gt 0 -and $nodes.Count -lt 120) {
            $entry = $queue.Dequeue()
            $element = $entry.element
            $current = $element.Current
            # Deliberately omit Name, Value, window title and text: they may contain jobs.
            $nodes.Add([pscustomobject]@{
                depth = $entry.depth
                control_type = $current.ControlType.ProgrammaticName
                class_name = ([string]$current.ClassName).Substring(0, [Math]::Min(120, ([string]$current.ClassName).Length))
                has_automation_id = -not [string]::IsNullOrEmpty($current.AutomationId)
                enabled = $current.IsEnabled
                patterns = @($element.GetSupportedPatterns() | ForEach-Object { $_.ProgrammaticName })
            })
            if ($entry.depth -lt 3) {
                $child = $walker.GetFirstChild($element)
                $siblings = 0
                while ($child -and $siblings -lt 40 -and $queue.Count -lt 120) {
                    $queue.Enqueue(@{ element = $child; depth = $entry.depth + 1 })
                    $child = $walker.GetNextSibling($child)
                    $siblings++
                }
                if ($child) { $result.truncated = $true }
            }
        }
        $result.nodes = @($nodes.ToArray())
        $result.truncated = $result.truncated -or $queue.Count -gt 0
        $result.state = 'observed'
    } catch { $result.state = 'unavailable' }
    return [pscustomobject]$result
}

function Get-StationEvidence {
    param([switch]$SkipAccessibility, [switch]$SkipNativeWindows)
    $issues = New-Object 'System.Collections.Generic.List[string]'
    $targets = New-Object 'System.Collections.Generic.List[object]'
    foreach ($process in @(Get-Process)) {
        $name = $process.ProcessName
        # Avoid inspecting paths or windows of unrelated applications.
        if ($name -notmatch '^(PrintExp(?:[_-].*)?|NWReceive|App2?|Production Manager|ProductionManager|FlexiPRINT|FlexiSign(?:Pro)?)$') { continue }
        $path = $null
        try { $path = $process.Path } catch { }
        if (-not (Test-TargetProcess -Name $name -ExecutablePath $path)) { continue }
        $version = $null
        try { $version = $process.MainModule.FileVersionInfo.FileVersion } catch { }
        $accessibility = [pscustomobject]@{ state = 'skipped'; nodes = @(); truncated = $false }
        if (-not $SkipAccessibility) {
            try { $accessibility = Get-AccessibilityEvidence -WindowHandle $process.MainWindowHandle } catch { }
        }
        $native = [pscustomobject]@{ state = 'skipped'; nodes = @(); truncated = $false }
        if (-not $SkipNativeWindows) {
            $native = Get-Win32WindowEvidence -TargetProcessId $process.Id
        }
        $targets.Add([pscustomobject]@{
            process_name = $name; process_id = $process.Id; file_version = $version
            accessibility = $accessibility
            native_windows = $native
        })
    }
    $connections = New-Object 'System.Collections.Generic.List[object]'
    $tcpState = 'not_requested_no_target'
    if ($targets.Count -gt 0) {
        try {
            # Queries existing OS records only. Does not connect, scan or send packets.
            $tcp = @(Get-NetTCPConnection -ErrorAction Stop)
            foreach ($connection in $tcp) {
                if ($connection.OwningProcess -notin @($targets | ForEach-Object { $_.process_id })) { continue }
                if ($connections.Count -ge 300) { $issues.Add('tcp_list_truncated'); break }
                $connections.Add([pscustomobject]@{
                    process_id = $connection.OwningProcess
                    state = [string]$connection.State
                    local_port = $connection.LocalPort
                    remote_port = $connection.RemotePort
                    local_address_kind = Get-EndpointKind $connection.LocalAddress
                    remote_address_kind = Get-EndpointKind $connection.RemoteAddress
                })
            }
            $tcpState = 'observed'
        } catch { $tcpState = 'unavailable'; $issues.Add('tcp_inventory_unavailable') }
    }
    return [pscustomobject][ordered]@{
        schema_version = 3; mode = 'observe_only'; machine_status = 'NAO_VERIFICADO'
        collected_at = [DateTime]::UtcNow.ToString('o')
        powershell_version = $PSVersionTable.PSVersion.ToString()
        processes = @($targets.ToArray()); tcp_state = $tcpState
        connections = @($connections.ToArray())
        associations = @((Get-OpenAssociation '.prt'), (Get-OpenAssociation '.prn'))
        issues = @($issues.ToArray())
    }
}

function Save-StationEvidence {
    param([Parameter(Mandatory)]$Evidence, [Parameter(Mandatory)][string]$ParentDirectory)
    $root = Get-Item -LiteralPath $ParentDirectory -ErrorAction Stop
    if (-not $root.PSIsContainer -or -not [System.IO.Path]::IsPathRooted($ParentDirectory)) { throw 'Selecione uma pasta absoluta existente.' }
    $destination = Join-Path $root.FullName ('FluxoRIP-Diagnostico-' + [Guid]::NewGuid().ToString('N'))
    $null = New-Item -ItemType Directory -Path $destination -ErrorAction Stop
    $report = Join-Path $destination 'diagnostico.json'
    $json = $Evidence | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText($report, $json, (New-Object System.Text.UTF8Encoding($false)))
    return $report
}

if ($MyInvocation.InvocationName -ne '.') {
    try {
        if ([Environment]::OSVersion.Platform -ne 'Win32NT') { throw 'Este diagnostico deve ser executado no Windows.' }
        if (-not $OutputDirectory) {
            if ($NonInteractive) { throw 'Informe OutputDirectory.' }
            Add-Type -AssemblyName System.Windows.Forms
            $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
            $dialog.Description = 'Selecione onde salvar o diagnostico do Fluxo RIP.'
            if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
            $OutputDirectory = $dialog.SelectedPath
        }
        Write-Host 'Coletando informacoes de leitura. Mantenha PrintExp e Production Manager abertos.'
        $evidence = Get-StationEvidence -SkipAccessibility:$SkipAccessibility -SkipNativeWindows:$SkipNativeWindows
        $report = Save-StationEvidence -Evidence $evidence -ParentDirectory $OutputDirectory
        Write-Host ('Relatorio criado: ' + $report)
        Write-Host ('Processos encontrados: ' + @($evidence.processes).Count)
        if (@($evidence.processes).Count -eq 0) { Write-Host 'Abra os programas de impressao e execute novamente para observar os processos.' }
        Write-Host 'Nenhum trabalho ou comando foi enviado. Voce pode revisar o JSON antes de compartilhar.'
    } catch {
        Write-Error 'Nao foi possivel concluir o diagnostico. Nenhuma configuracao de impressora foi alterada.'
        exit 1
    }
}
