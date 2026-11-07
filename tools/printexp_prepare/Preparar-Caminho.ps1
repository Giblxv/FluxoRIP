#requires -version 5.1
[CmdletBinding()]
param([switch]$Prepare, [switch]$NoDialogs, [string]$ReportDirectory)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Initialize-FileDialogGuard {
    if (-not ('FluxoRIP.PrepareOnlyV1.FileDialogGuard' -as [type])) {
        Add-Type -Path (Join-Path $PSScriptRoot 'FileDialogGuard.cs')
    }
}

function Get-PreparationTarget {
    $targets = @(Get-Process | Where-Object { $_.ProcessName -match '^PrintExp(?:[_-].*)?$' })
    if ($targets.Count -ne 1) { return [pscustomobject]@{ state='expected_one_printexp_process'; process_id=$null; inspection=$null } }
    $inspection = [FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Inspect($targets[0].Id)
    return [pscustomobject]@{ state=$inspection.State; process_id=$targets[0].Id; inspection=$inspection }
}

function New-PreparationReport {
    return [pscustomobject][ordered]@{
        schema_version=1; mode='inspect_only'; machine_status='NAO_VERIFICADO'
        collected_at=[DateTime]::UtcNow.ToString('o'); state='not_started'
        candidate_count=0; input_empty=$null; operator_approved=$false
        write_attempted=$false; write_accepted=$false; path_verified=$false
        dialog_still_open=$false; helper_confirmed_file=$false; helper_requested_print=$false
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    $report = New-PreparationReport
    if ($Prepare) { $report.mode = 'prepare_path_only' }
    $reportFile = $null
    try {
        if ([Environment]::OSVersion.Platform -ne 'Win32NT') { throw 'windows_required' }
        if ($Prepare -and $NoDialogs) { throw 'interactive_confirmation_required' }
        if (-not $ReportDirectory) { $ReportDirectory = $PSScriptRoot }
        $parent = Get-Item -LiteralPath $ReportDirectory
        if (-not $parent.PSIsContainer -or -not [System.IO.Path]::IsPathRooted($parent.FullName)) { throw 'report_directory_invalid' }
        $folder = Join-Path $parent.FullName ('FluxoRIP-Preparacao-' + [Guid]::NewGuid().ToString('N'))
        $null = New-Item -ItemType Directory -Path $folder
        $reportFile = Join-Path $folder 'resultado.json'
        [System.IO.File]::WriteAllText($reportFile, ($report | ConvertTo-Json -Depth 5), (New-Object System.Text.UTF8Encoding($false)))
        Initialize-FileDialogGuard
        $target = Get-PreparationTarget
        $report.state = $target.state
        if ($target.inspection) {
            $report.candidate_count = $target.inspection.CandidateCount
            $report.input_empty = $target.inspection.InputEmpty
        }
        if ($Prepare -and $target.inspection -and $target.inspection.CanPrepare) {
            Add-Type -AssemblyName System.Windows.Forms
            $picker = New-Object System.Windows.Forms.OpenFileDialog
            try {
                $picker.Title = 'Fluxo RIP - escolher PRT/PRN apenas para preparar o caminho'
                $picker.Filter = 'Arquivos PRT/PRN|*.prt;*.prn'
                $picker.Multiselect = $false
                $picker.CheckFileExists = $true
                $picker.RestoreDirectory = $true
                if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
                    $report.state = 'operator_cancelled'
                } else {
                    $path = $picker.FileName
                    $validation = [FluxoRIP.PrepareOnlyV1.FileDialogGuard]::ValidateLocalFile($path)
                    if ($validation -ne 'valid') {
                        $report.state = $validation
                    } else {
                        $message = "Preencher somente o campo de nome do arquivo na janela ja aberta do PrintExp?`n`n$path`n`nA abertura do arquivo e a impressao continuam manuais."
                        $answer = [System.Windows.Forms.MessageBox]::Show($message, 'Fluxo RIP - confirmar preparacao do caminho', [System.Windows.Forms.MessageBoxButtons]::YesNo, [System.Windows.Forms.MessageBoxIcon]::Question, [System.Windows.Forms.MessageBoxDefaultButton]::Button2)
                        if ($answer -eq [System.Windows.Forms.DialogResult]::Yes) {
                            $report.operator_approved = $true
                            $outcome = [FluxoRIP.PrepareOnlyV1.FileDialogGuard]::Prepare($target.inspection.Token, $path)
                            $report.state = $outcome.State
                            $report.write_attempted = $outcome.WriteAttempted
                            $report.write_accepted = $outcome.WriteAccepted
                            $report.path_verified = $outcome.PathVerified
                            $report.dialog_still_open = $outcome.DialogStillOpen
                        } else { $report.state = 'operator_cancelled' }
                    }
                }
            } finally { $picker.Dispose() }
        }
    } catch {
        if ($_.Exception.Message -in @('windows_required','interactive_confirmation_required','report_directory_invalid')) {
            $report.state = $_.Exception.Message
        } else { $report.state = 'preparation_unavailable' }
    }
    if ($reportFile) {
        try {
            [System.IO.File]::WriteAllText($reportFile, ($report | ConvertTo-Json -Depth 5), (New-Object System.Text.UTF8Encoding($false)))
            Write-Host ('Relatorio: ' + $reportFile)
        } catch { $reportFile = $null; Write-Host 'O relatorio nao pode ser salvo. Confira o resultado na tela.' }
    }
    Write-Host ('Resultado: ' + $report.state)
    if (-not $NoDialogs) {
        Add-Type -AssemblyName System.Windows.Forms
        $message = 'Resultado: ' + $report.state + "`n`n"
        if ($report.path_verified) {
            $message += 'Caminho preparado. Para encerrar este ensaio, confira o campo e cancele manualmente a janela do PrintExp. Abertura e impressao nao foram solicitadas pelo assistente.'
        } elseif ($report.state -eq 'input_not_empty') {
            $message += 'O campo de nome de arquivo do PrintExp ja contem texto. Deixe-o vazio manualmente, mantenha a janela aberta e execute novamente.'
        } elseif ($report.state -eq 'ready_for_manual_preparation') {
            $message += 'Janela de abertura reconhecida com campo vazio. Para o ensaio de preenchimento, execute PREPARAR_CAMINHO.cmd.'
        } elseif ($report.state -in @('path_invalid','not_local_drive','file_missing','file_not_regular','parent_is_link','file_empty','file_unavailable','path_not_normalized')) {
            $message += 'Escolha um PRT/PRN existente, nao vazio, em disco local, com caminho de ate 259 caracteres. Links, pastas de rede e arquivos de nuvem com redirecionamento ficam fora deste primeiro ensaio. Consulte o LEIAME.'
        } elseif ($report.state -eq 'operator_cancelled') {
            $message += 'Ensaio cancelado pelo operador.'
        } elseif ($report.state -in @('dialog_changed','inspection_expired','preparation_not_confirmed','preparation_unavailable','input_unreadable','inspection_unavailable')) {
            $message += 'Nao foi possivel confirmar a preparacao. Confira a janela manualmente. Nao ha repeticao automatica.'
        } else {
            $message += 'Consulte o LEIAME. E necessario manter uma unica instancia do PrintExp com a janela Abrir arquivo aberta. O assistente reconhece botoes Open/Abrir e Cancel/Cancelar.'
        }
        if ($reportFile) { $message += "`n`nRelatorio: " + $reportFile }
        $null = [System.Windows.Forms.MessageBox]::Show($message, 'Fluxo RIP - resultado da preparacao')
    }
}
