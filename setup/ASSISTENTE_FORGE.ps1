param([Parameter(Mandatory=$true)][string]$ForgeExe)
# Assistente Fluxo RIP - Windows PowerShell 5.1, Windows 10 e 11
# Nenhuma configuracao da rede ou da controladora Hoson e modificada.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

if (-not (Test-Path -LiteralPath $ForgeExe -PathType Leaf)) { throw 'FluxoRIP.exe nao encontrado.' }
$base = Join-Path $env:LOCALAPPDATA 'FORGE'
New-Item -ItemType Directory -Path $base -Force | Out-Null
$profilePath = Join-Path $base 'modo_inicial.json'
$stationConfigPath = Join-Path $base 'estacao.json'
$authPath = Join-Path $base 'central_auth.json'
$agentPidPath = Join-Path $base 'agente.pid'

function Mensagem([string]$texto, [string]$titulo='Fluxo RIP') {
  [System.Windows.Forms.MessageBox]::Show($texto, $titulo, [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
}
function Falha([string]$texto) {
  [System.Windows.Forms.MessageBox]::Show($texto, 'Fluxo RIP - Atencao', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning) | Out-Null
}
function SalvarJson($path, $obj, [bool]$privado=$false) {
  $tmp = "$path.tmp"
  $json = ConvertTo-Json -InputObject $obj -Compress -Depth 6
  [System.IO.File]::WriteAllText($tmp, $json, (New-Object System.Text.UTF8Encoding($false)))
  Move-Item -Force -LiteralPath $tmp -Destination $path
  if ($privado) {
    try {
      $acl = New-Object System.Security.AccessControl.FileSecurity
      $user = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
      $acl.SetOwner($user)
      $acl.SetAccessRuleProtection($true,$false)
      $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($user,'FullControl','Allow')
      $acl.AddAccessRule($rule)
      Set-Acl -LiteralPath $path -AclObject $acl
    } catch { throw 'Nao foi possivel restringir permissao do arquivo com a chave. Verifique o NTFS.' }
  }
}
function IniciarExe([string[]]$argumentos=@()) {
  if ($argumentos.Count -gt 0) {
    return Start-Process -FilePath $ForgeExe -ArgumentList $argumentos -WorkingDirectory (Split-Path -Parent $ForgeExe) -PassThru
  }
  return Start-Process -FilePath $ForgeExe -WorkingDirectory (Split-Path -Parent $ForgeExe) -PassThru
}
function ValidarIpCentral([string]$ip) {
  $addr = $null
  if (-not [System.Net.IPAddress]::TryParse($ip, [ref]$addr) -or $addr.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork) {
    throw 'Informe um endereco IPv4 valido da rede administrativa.'
  }
  $b = $addr.GetAddressBytes()
  $private = ($b[0] -eq 10) -or ($b[0] -eq 172 -and $b[1] -ge 16 -and $b[1] -le 31) -or ($b[0] -eq 192 -and $b[1] -eq 168)
  if (-not $private -or ($b[0] -eq 192 -and $b[1] -eq 168 -and $b[2] -eq 127)) {
    throw 'Use um IPv4 privado da rede administrativa, nao 192.168.127.x da Hoson.'
  }
  return $addr.ToString()
}
function AdicionarLabel($parent,[string]$texto,[int]$x,[int]$y,[int]$largura=640,[int]$altura=44) {
  $l = New-Object System.Windows.Forms.Label
  $l.Text=$texto; $l.SetBounds($x,$y,$largura,$altura)
  $l.ForeColor = [System.Drawing.Color]::FromArgb(215,225,227)
  $parent.Controls.Add($l)
  return $l
}
function AdicionarBotao($parent,[string]$texto,[int]$x,[int]$y,[int]$w=215,[int]$h=42) {
  $b = New-Object System.Windows.Forms.Button
  $b.Text = $texto; $b.SetBounds($x,$y,$w,$h)
  $b.FlatStyle=[System.Windows.Forms.FlatStyle]::Flat
  $b.BackColor=[System.Drawing.Color]::FromArgb(54,79,72)
  $b.ForeColor=[System.Drawing.Color]::White
  $parent.Controls.Add($b)
  return $b
}
function AdicionarTexto($parent,[int]$x,[int]$y,[int]$w=380,[string]$valor='') {
  $txt = New-Object System.Windows.Forms.TextBox
  $txt.SetBounds($x,$y,$w,27); $txt.Text=$valor
  $parent.Controls.Add($txt)
  return $txt
}

$form = New-Object System.Windows.Forms.Form
$form.Text='Fluxo RIP - Configuracao simples'
$form.ClientSize=New-Object System.Drawing.Size(790,605)
$form.StartPosition=[System.Windows.Forms.FormStartPosition]::CenterScreen
$form.BackColor=[System.Drawing.Color]::FromArgb(31,38,42)
$form.ForeColor=[System.Drawing.Color]::White
$form.Font=New-Object System.Drawing.Font('Segoe UI',10)
$form.FormBorderStyle='FixedDialog'
$form.MaximizeBox=$false
AdicionarLabel $form 'Fluxo RIP | Configuracao de producao' 24 16 720 30 | Out-Null
AdicionarLabel $form 'Escolha uma funcao para este computador. Na proxima abertura, o Fluxo RIP inicia automaticamente no modo salvo.' 24 48 740 40 | Out-Null

$tabs = New-Object System.Windows.Forms.TabControl
$tabs.SetBounds(24,94,741,401)
$tabs.Font=New-Object System.Drawing.Font('Segoe UI',10)
$form.Controls.Add($tabs)
foreach ($nome in @('Uso local','Computador Central','Estacao da impressora')) {
  $page = New-Object System.Windows.Forms.TabPage
  $page.Text=$nome; $page.BackColor=[System.Drawing.Color]::FromArgb(40,49,53)
  $page.ForeColor=[System.Drawing.Color]::White
  $tabs.TabPages.Add($page)
}
$local=$tabs.TabPages[0]; $central=$tabs.TabPages[1]; $station=$tabs.TabPages[2]

AdicionarLabel $local 'Use o Fluxo RIP sozinho, neste computador. Nao precisa de IP, senha ou chave.' 23 30 665 53 | Out-Null
$localBtn=AdicionarBotao $local 'Abrir Fluxo RIP (uso local)' 23 113 300 48
$localBtn.Add_Click({
  try {
    SalvarJson $profilePath @{modo='local'}
    $null=IniciarExe
    $form.Close()
  } catch { Falha $_.Exception.Message }
})
AdicionarLabel $local 'Se voce tem somente um PC de trabalho, essa e a escolha mais simples.' 23 193 655 50 | Out-Null

AdicionarLabel $central 'O computador principal compartilha projetos e filas com os demais PCs pela rede administrativa.' 22 18 675 44 | Out-Null
AdicionarLabel $central '1. Selecione o IPv4 da rede administrativa (NAO escolha 192.168.127.x):' 22 75 680 26 | Out-Null
$centralIp=New-Object System.Windows.Forms.ComboBox
$centralIp.SetBounds(22,106,350,30)
$centralIp.DropDownStyle='DropDown'
$central.Controls.Add($centralIp)
try {
  $addresses = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop | Where-Object {
    ($_.AddressState -eq 'Preferred') -and ($_.IPAddress -notmatch '^(127\.|169\.254\.|192\.168\.127\.)')
  } | Select-Object -ExpandProperty IPAddress -Unique)
  foreach ($ip in $addresses) { try { $null=ValidarIpCentral $ip; $null=$centralIp.Items.Add($ip) } catch {} }
  if ($centralIp.Items.Count -gt 0) { $centralIp.SelectedIndex=0 }
} catch {}
AdicionarLabel $central 'Porta:' 390 107 60 30 | Out-Null
$centralPort=AdicionarTexto $central 450 105 90 '8765'
$createBtn=AdicionarBotao $central '1. Criar senha de acesso' 22 162 260 42
$createBtn.Add_Click({
  try {
    if (Test-Path $authPath) { Mensagem 'A Central ja tem credenciais. Para preservar os agentes existentes, elas nao foram redefinidas.'; return }
    $processo=IniciarExe -argumentos @('--configurar-central')
    $processo.WaitForExit()
    if ($processo.ExitCode -ne 0 -or -not (Test-Path $authPath)) { throw 'A criacao de senha nao foi concluida.' }
    Mensagem 'Senha criada. Guarde a senha exibida na janela anterior. Voce podera mostrar a chave dos agentes a qualquer momento.'
  } catch { Falha $_.Exception.Message }
})
$tokenBtn=AdicionarBotao $central 'Mostrar chave das estacoes' 300 162 255 42
$tokenBtn.Add_Click({
  try {
    if (-not (Test-Path $authPath)) { throw 'Primeiro crie a senha da Central.' }
    $null=IniciarExe -argumentos @('--chave-agente')
  } catch { Falha $_.Exception.Message }
})
$centralBtn=AdicionarBotao $central '2. Iniciar Central' 22 242 310 48
$centralBtn.Add_Click({
  try {
    $ip=ValidarIpCentral $centralIp.Text.Trim()
    if (-not ($centralIp.Items.Contains($ip))) { throw 'Escolha um IP atribuido a este computador na lista.' }
    $port=0
    if (-not [int]::TryParse($centralPort.Text.Trim(),[ref]$port) -or $port -lt 1024 -or $port -gt 65535) { throw 'A porta deve estar entre 1024 e 65535.' }
    if (-not (Test-Path $authPath)) { throw 'Clique primeiro em Criar senha de acesso.' }
    $decision=[System.Windows.Forms.MessageBox]::Show('Use a Central somente na rede interna confiavel. O acesso HTTP sem HTTPS nao deve ser exposto a Internet. Continuar?', 'Fluxo RIP - Seguranca',[System.Windows.Forms.MessageBoxButtons]::YesNo,[System.Windows.Forms.MessageBoxIcon]::Warning)
    if ($decision -ne [System.Windows.Forms.DialogResult]::Yes) { return }
    SalvarJson $profilePath @{modo='central';ip=$ip;porta=$port}
    Mensagem "Central configurada.`nEndereco para outros PCs: http://${ip}:$port`nUsuario: forge`nUse a senha criada anteriormente.`n`nSe o Firewall perguntar, permita apenas na rede Privada."
    $null=IniciarExe
    $form.Close()
  } catch { Falha $_.Exception.Message }
})
AdicionarLabel $central 'Recomendado: mantenha o computador Central ligado durante a producao.' 22 309 660 45 | Out-Null

AdicionarLabel $station 'Esta estacao informa a Central sobre suas placas de rede e os IPs Hoson encontrados.' 22 12 680 36 | Out-Null
AdicionarLabel $station 'IP da Central:' 22 61 150 25 | Out-Null
$stationIp=AdicionarTexto $station 190 58 220 '192.168.1.100'
AdicionarLabel $station 'Porta:' 420 61 60 26 | Out-Null
$stationPort=AdicionarTexto $station 476 58 83 '8765'
AdicionarLabel $station 'Nome desta estacao:' 22 105 180 26 | Out-Null
$stationName=AdicionarTexto $station 190 103 370 $env:COMPUTERNAME
AdicionarLabel $station 'Chave de agente (copie da Central):' 22 149 298 26 | Out-Null
$stationToken=AdicionarTexto $station 320 146 335 ''
$stationToken.UseSystemPasswordChar=$true
$scanCheck=New-Object System.Windows.Forms.CheckBox
$scanCheck.SetBounds(22,190,645,45)
$scanCheck.Text='Verificar a rede Hoson uma vez ao iniciar (opcional)'
$scanCheck.ForeColor=[System.Drawing.Color]::White
$station.Controls.Add($scanCheck)
$stationBtn=AdicionarBotao $station 'Conectar e iniciar esta estacao' 22 252 370 46
$stationBtn.Add_Click({
  try {
    $ip=ValidarIpCentral $stationIp.Text.Trim()
    $port=0
    if (-not [int]::TryParse($stationPort.Text.Trim(),[ref]$port) -or $port -lt 1024 -or $port -gt 65535) { throw 'Porta da Central invalida.' }
    $name=$stationName.Text.Trim()
    if ($name.Length -lt 2 -or $name.Length -gt 120) { throw 'Informe um nome de estacao entre 2 e 120 caracteres.' }
    $token=$stationToken.Text.Trim()
    if ($token.Length -lt 24 -or $token.Length -gt 256) { throw 'Cole a chave completa, exibida na Central.' }
    $url="http://${ip}:$port"
    # Testar se a Central esta ativa e protegida antes de salvar a chave.
    try {
      $response=Invoke-WebRequest -Uri "$url/api/health" -UseBasicParsing -TimeoutSec 7 -ErrorAction Stop
      if ($response.StatusCode -eq 200) { throw 'O servidor nao parece exigir autenticacao. Abra a Central no modo protegido.' }
    } catch [System.Net.WebException] {
      $webResponse=$_.Exception.Response
      if ($null -eq $webResponse -or [int]$webResponse.StatusCode -ne 401) {
        throw 'Nao foi possivel acessar a Central protegida. Verifique IP, porta, firewall e rede administrativa.'
      }
    }
    SalvarJson $stationConfigPath @{central_url=$url;station_name=$name;agent_token=$token;scan_on_start=[bool]$scanCheck.Checked} $true
    $probe=IniciarExe -argumentos @('--testar-agente')
    $probe.WaitForExit()
    if ($probe.ExitCode -ne 0) { throw 'A Central nao confirmou o teste. Confira a chave e a rede.' }
    SalvarJson $profilePath @{modo='estacao'}
    $agent=IniciarExe
    [System.IO.File]::WriteAllText($agentPidPath, [string]$agent.Id)
    Mensagem 'Estacao conectada! O agente foi iniciado e enviara atualizacoes a cada 120 segundos. Para interromper, use o Gerenciador de Tarefas ou reabra este assistente.'
    $form.Close()
  } catch { Falha $_.Exception.Message }
})
$stopBtn=AdicionarBotao $station 'Parar agente desta estacao' 415 252 258 46
$stopBtn.Add_Click({
  try {
    if (-not (Test-Path $agentPidPath)) { throw 'Nao foi encontrado um agente iniciado por este assistente.' }
    $idTexto=[System.IO.File]::ReadAllText($agentPidPath).Trim()
    $identificador=0
    if (-not [int]::TryParse($idTexto,[ref]$identificador)) { throw 'Identificador de processo invalido.' }
    $processo=Get-Process -Id $identificador -ErrorAction Stop
    if ($processo.Path -ne $ForgeExe) { throw 'Processo diferente do Fluxo RIP: nao sera encerrado.' }
    Stop-Process -Id $identificador -ErrorAction Stop
    Remove-Item $agentPidPath -Force
    Mensagem 'Agente interrompido.'
  } catch { Falha $_.Exception.Message }
})

$folderBtn=AdicionarBotao $form 'Abrir meus dados' 24 522 213 40
$folderBtn.Add_Click({ Start-Process -FilePath 'explorer.exe' -ArgumentList @($base) })
$logBtn=AdicionarBotao $form 'Ver log de erros' 250 522 213 40
$logBtn.Add_Click({
  $log = Join-Path $base 'forge.log'
  if (Test-Path $log) { Start-Process -FilePath 'notepad.exe' -ArgumentList @($log) }
  else { Mensagem 'Nenhum log foi criado ainda.' }
})
$closeBtn=AdicionarBotao $form 'Fechar assistente' 477 522 285 40
$closeBtn.Add_Click({ $form.Close() })

# Priorizar a aba do papel salvo para evitar refazer a configuracao.
try {
  if (Test-Path $profilePath) {
    $saved=Get-Content -Raw -Encoding UTF8 $profilePath | ConvertFrom-Json
    if ($saved.modo -eq 'central') { $tabs.SelectedIndex=1; $centralIp.Text=[string]$saved.ip; $centralPort.Text=[string]$saved.porta }
    if ($saved.modo -eq 'estacao') { $tabs.SelectedIndex=2 }
  }
} catch { }
[void]$form.ShowDialog()
