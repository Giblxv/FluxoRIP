# Windows PowerShell 5.1 / Windows 10 e 11
# Configure somente em uma estacao de producao autorizada.
$ErrorActionPreference = 'Stop'
$base = Join-Path $env:LOCALAPPDATA 'FORGE'
New-Item -ItemType Directory -Force -Path $base | Out-Null
$central = Read-Host 'URL da Central (ex.: http://192.168.1.100:8765)'
$name = Read-Host 'Nome desta estacao (ex.: DTF-01)'
$secure = Read-Host 'Cole a chave de agente gerada na Central' -AsSecureString
$bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $key = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
finally { [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
$allowScan = (Read-Host 'Fazer um scan de IPs 192.168.127.x apenas na PRIMEIRA inicializacao? (s/N)') -match '^[Ss]'
$config = @{ central_url=$central; station_name=$name; agent_token=$key; scan_on_start=[bool]$allowScan }
$path = Join-Path $base 'estacao.json'
$json = $config | ConvertTo-Json -Depth 3
[System.IO.File]::WriteAllText($path, $json, (New-Object System.Text.UTF8Encoding($false)))
# Restrinja o arquivo de configuracao ao usuario que executa o agente.
try {
  $user = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
  $acl = Get-Acl $path
  $acl.SetAccessRuleProtection($true,$false)
  $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($user,'FullControl','Allow')
  $acl.AddAccessRule($rule)
  Set-Acl $path $acl
} catch { Write-Warning 'Nao foi possivel ajustar permissoes NTFS automaticamente; revise quem acessa estacao.json.' }
Write-Host "Configuracao salva em $path" -ForegroundColor Green
Write-Host 'Agora execute TESTAR_ESTACAO.bat e depois INICIAR_AGENTE.bat.'
