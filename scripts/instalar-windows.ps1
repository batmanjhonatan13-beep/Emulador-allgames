<#
  AllGames no Windows: instala e configura tudo para jogar os emuladores pelo celular.

  Como usar: abra o PowerShell (menu Iniciar > digite PowerShell) e cole:

    irm https://raw.githubusercontent.com/batmanjhonatan13-beep/Emulador-allgames/ccr-f2ccb85d-qka26y/scripts/instalar-windows.ps1 | iex

  O script pede permissão de administrador, instala pelo winget o Sunshine (transmite
  para o celular), o RetroArch e o Python, baixa o AllGames e os emuladores, e coloca o
  app "AllGames" no Moonlight. Pode rodar de novo quando quiser: ele só atualiza.

  Não baixa jogos: no fim ele pergunta se você quer copiar os seus de uma pasta.
#>
param(
    [string]$Repositorio = "batmanjhonatan13-beep/Emulador-allgames",
    [string]$Versao = "ccr-f2ccb85d-qka26y",
    [string]$PastaDosJogos = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # deixa os downloads bem mais rápidos

function Passo($texto) { Write-Host "`n==> $texto" -ForegroundColor Cyan }
function Aviso($texto) { Write-Host " !  $texto" -ForegroundColor Yellow }
function Falha($texto) {
    Write-Host "`nERRO: $texto" -ForegroundColor Red
    Read-Host "Aperte Enter para fechar"
    exit 1
}

# --- Administrador ------------------------------------------------------------------
# Instalar programas e configurar o Sunshine precisa de administrador. Se colaram a linha
# do irm num PowerShell comum, o script se copia para um arquivo e abre de novo como admin.
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Pedindo permissão de administrador (clique em Sim)..."
    $arquivo = $PSCommandPath
    if (-not $arquivo) {
        # Veio pelo "irm ... | iex": não há arquivo para reabrir, então baixa de novo. O
        # PowerShell do Windows só lê os acentos certo com UTF-8 com BOM (o -Encoding UTF8 dele).
        $arquivo = Join-Path $env:TEMP "instalar-allgames.ps1"
        $url = "https://raw.githubusercontent.com/$Repositorio/$Versao/scripts/instalar-windows.ps1"
        (Invoke-WebRequest -Uri $url -UseBasicParsing).Content | Set-Content -Path $arquivo -Encoding UTF8
    }
    $argumentos = "-NoProfile -ExecutionPolicy Bypass -File `"$arquivo`" -Repositorio `"$Repositorio`" -Versao `"$Versao`""
    if ($PastaDosJogos) { $argumentos += " -PastaDosJogos `"$PastaDosJogos`"" }
    Start-Process powershell -Verb RunAs -ArgumentList $argumentos
    exit
}

Write-Host "AllGames: cloud gaming pessoal no seu PC" -ForegroundColor Green
Write-Host "Isto leva de 10 a 30 minutos, dependendo da internet. Não feche esta janela."

# --- winget -------------------------------------------------------------------------
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Falha "o winget não está no PC. Abra a Microsoft Store, instale o 'Instalador de Aplicativo' e rode de novo."
}

# Devolve o primeiro dos caminhos que existe (os programas podem cair em mais de um lugar).
function Achar($caminhos) { $caminhos | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1 }

function Instalar($id, $nome, $caminhos, $escopo) {
    $achado = Achar $caminhos
    if ($achado) {
        Write-Host "    $nome já está instalado"
        return $achado
    }
    Write-Host "    instalando $nome"
    $parametros = @("install", "--id", $id, "-e", "--silent", "--accept-package-agreements", "--accept-source-agreements")
    if ($escopo) { $parametros += @("--scope", $escopo) }
    & winget @parametros | Out-Null
    $achado = Achar $caminhos
    if (-not $achado) { Falha "não consegui instalar o $nome (winget $($parametros -join ' '))" }
    return $achado
}

Passo "Instalando os programas"
$sunshineExe = Instalar "LizardByte.Sunshine" "Sunshine (transmite para o celular)" @(
    (Join-Path $env:ProgramFiles "Sunshine\sunshine.exe")) $null
$retroarch = Instalar "Libretro.RetroArch" "RetroArch (emuladores)" @(
    "C:\RetroArch-Win64\retroarch.exe",
    (Join-Path $env:ProgramFiles "RetroArch\retroarch.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\RetroArch\retroarch.exe")) $null
$python = Instalar "Python.Python.3.12" "Python (roda o AllGames)" @(
    (Join-Path $env:ProgramFiles "Python312\python.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe")) "machine"
# O AllGames acha o RetroArch sozinho, mas se ele caiu em outro lugar fica anotado.
[Environment]::SetEnvironmentVariable("ALLGAMES_RETROARCH", $retroarch, "User")
$env:ALLGAMES_RETROARCH = $retroarch
# Python em UTF-8: nomes com acento (Pokémon) certos nos arquivos, inclusive no Sunshine.
[Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
$env:PYTHONUTF8 = "1"

# --- AllGames -----------------------------------------------------------------------
Passo "Baixando o AllGames"
$base = Join-Path $env:USERPROFILE "AllGames"
$app = Join-Path $base "app"
$zip = Join-Path $env:TEMP "allgames.zip"
$extraido = Join-Path $env:TEMP "allgames-extraido"
Invoke-WebRequest -Uri "https://github.com/$Repositorio/archive/refs/heads/$Versao.zip" -OutFile $zip -UseBasicParsing
Remove-Item $extraido -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive -Path $zip -DestinationPath $extraido -Force
$pastaDoZip = Get-ChildItem $extraido -Directory | Select-Object -First 1
# Só o programa é trocado: jogos, saves e emuladores ficam em AllGames\roms e AllGames\emuladores.
Remove-Item $app -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $base -Force | Out-Null
Move-Item $pastaDoZip.FullName $app
Remove-Item $zip, $extraido -Recurse -Force -ErrorAction SilentlyContinue
$allgames = Join-Path $app "bin\allgames"

function AllGames {
    & $python $allgames @args
    if ($LASTEXITCODE -ne 0) { Aviso "allgames $($args -join ' ') terminou com aviso (código $LASTEXITCODE)" }
}

# --- Jogos --------------------------------------------------------------------------
Passo "Pastas dos jogos"
AllGames roms
if (-not $PastaDosJogos) {
    Write-Host ""
    Write-Host "Você tem uma pasta com os SEUS jogos (ROMs)? Por exemplo a pasta 'roms' do cartão"
    Write-Host "de um R36S/ArkOS, um pendrive ou um HD. Ela pode ter uma pasta por console."
    $resposta = Read-Host "Digite S para escolher a pasta agora, ou só Enter para pular"
    if ($resposta -match "^[sS]") {
        Add-Type -AssemblyName System.Windows.Forms
        $dialogo = New-Object System.Windows.Forms.FolderBrowserDialog
        $dialogo.Description = "Escolha a pasta com os seus jogos (uma pasta por console: snes, gba, psx...)"
        if ($dialogo.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { $PastaDosJogos = $dialogo.SelectedPath }
    }
}
if ($PastaDosJogos) {
    Write-Host "    copiando de $PastaDosJogos (pode demorar)"
    robocopy $PastaDosJogos (Join-Path $base "roms") /E /XO /R:1 /W:1 /NFL /NDL /NJH /NP | Out-Null
}

# --- Emuladores ---------------------------------------------------------------------
Passo "Baixando os emuladores e as capas (só na primeira vez demora)"
AllGames preparar

# --- Sunshine -----------------------------------------------------------------------
Passo "Configurando o Sunshine"
$credenciais = Join-Path $env:ProgramFiles "Sunshine\config\sunshine_state.json"
$temLogin = (Test-Path $credenciais) -and ((Get-Content $credenciais -Raw) -match "username")
if (-not $temLogin) {
    Write-Host "Crie um usuário e uma senha para o painel do Sunshine (é onde você pareia o celular)."
    $usuario = Read-Host "Usuário"
    $senha = Read-Host "Senha" -AsSecureString
    $texto = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($senha))
    & $sunshineExe --creds $usuario $texto | Out-Null
}
# O AllGames atualiza a lista de apps do Sunshine (apps.json) sem precisar de administrador.
$appsJson = Join-Path $env:ProgramFiles "Sunshine\config\apps.json"
if (Test-Path $appsJson) { icacls $appsJson /grant "$($env:USERNAME):(M)" | Out-Null }
if (-not (Get-NetFirewallRule -DisplayName "Sunshine (AllGames)" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "Sunshine (AllGames)" -Program $sunshineExe -Action Allow -Profile Private, Domain | Out-Null
}
Set-Service -Name "SunshineService" -StartupType Automatic
Start-Service -Name "SunshineService" -ErrorAction SilentlyContinue
AllGames sincronizar

# --- Atalhos ------------------------------------------------------------------------
Passo "Criando atalhos na área de trabalho"
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$atalho = $shell.CreateShortcut((Join-Path $desktop "Jogos do AllGames.lnk"))
$atalho.TargetPath = Join-Path $base "roms"
$atalho.Save()
Set-Content -Path (Join-Path $desktop "Parear celular (Sunshine).url") -Value "[InternetShortcut]`r`nURL=https://localhost:47990/pin"

# --- Pronto -------------------------------------------------------------------------
Passo "Conferindo"
AllGames doutor
$ip = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object { $_.IPAddress -notmatch "^(127\.|169\.254\.)" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "Pronto! O AllGames está instalado." -ForegroundColor Green
Write-Host ""
Write-Host " 1. No celular, instale o app Moonlight (Play Store ou App Store)."
Write-Host " 2. No Moonlight, toque no + e digite o IP deste PC: $ip"
Write-Host " 3. O celular mostra um PIN. Abra o atalho 'Parear celular (Sunshine)' na área"
Write-Host "    de trabalho, entre com o usuário e a senha do Sunshine e digite o PIN."
Write-Host " 4. No Moonlight, toque em AllGames."
Write-Host ""
Write-Host "Seus jogos ficam em: $(Join-Path $base 'roms')  (atalho 'Jogos do AllGames')"
Read-Host "Aperte Enter para fechar"
