param(
    [string]$ValidationRoot = 'D:\code\kingai-sdk-validation',
    [string]$GoExecutable = 'go',
    [string]$MavenCommand = 'mvn.cmd'
)

# Windows sample tests only. No GN, Rust/Chromium builds or real account access.
$ErrorActionPreference = 'Stop'
$sourceRoot = Split-Path -Parent $PSScriptRoot
$root = [System.IO.Path]::GetFullPath($ValidationRoot)
if (-not $root.StartsWith('D:\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Keep downloaded dependencies, test outputs and caches on D:.'
}
foreach ($command in @($GoExecutable, $MavenCommand, 'python', 'node', 'npm.cmd')) {
    if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Required tool not found: $command" }
}
$names = @('GOCACHE','GOMODCACHE','GOPATH','GOTMPDIR','GOTOOLCHAIN','GOWORK','GOPROXY','GO111MODULE',
    'TEMP','TMP','MAVEN_OPTS','PYTHONDONTWRITEBYTECODE','PYTHONPATH','KINGAI_TEST_MCP','KINGAI_SOURCE_ROOT')
$previous = @{}
foreach ($name in $names) { $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$run = Join-Path $root ('runs\' + [guid]::NewGuid().ToString('N'))
function Invoke-SampleTestCommand {
    param([string]$Executable, [string[]]$CommandArguments)
    & $Executable @CommandArguments
    if ($LASTEXITCODE -ne 0) { throw "Sample validation failed: $Executable (exit $LASTEXITCODE)" }
}
try {
    foreach ($dir in @($root,$run,(Join-Path $run 'fixture'),(Join-Path $root 'tmp'))) {
        [void][System.IO.Directory]::CreateDirectory($dir)
    }
    $env:GOCACHE=Join-Path $root 'gocache'; $env:GOMODCACHE=Join-Path $root 'gomod'; $env:GOPATH=Join-Path $root 'gopath'
    $env:GOTMPDIR=Join-Path $root 'tmp'; $env:TEMP=$env:GOTMPDIR; $env:TMP=$env:TEMP
    $env:GOTOOLCHAIN='local'; $env:GOWORK='off'; $env:GOPROXY='https://goproxy.cn'
    $env:GO111MODULE='off'; $env:PYTHONDONTWRITEBYTECODE='1'
    $env:KINGAI_TEST_MCP=Join-Path $run 'fixture\KingAIMcpServer.exe'
    $env:KINGAI_SOURCE_ROOT=$sourceRoot
    Invoke-SampleTestCommand $GoExecutable @('build','-o',$env:KINGAI_TEST_MCP,(Join-Path $PSScriptRoot 'fixture\main.go'))
    [System.IO.File]::WriteAllText((Join-Path $run 'fixture\KingAIRuntime.exe'),'Test-only sentinel, never executed')
    $env:GO111MODULE='on'
    $env:PYTHONPATH=Join-Path $sourceRoot 'python'
    Invoke-SampleTestCommand 'python' @('-m','unittest','discover','-s',(Join-Path $sourceRoot 'python\tests'),'-v')

    $nodeRoot=Join-Path $run 'node'; [void][System.IO.Directory]::CreateDirectory($nodeRoot)
    Get-ChildItem -LiteralPath $sourceRoot -File | Where-Object { $_.Extension -in @('.mjs','.json','.ts') } | Copy-Item -Destination $nodeRoot
    foreach ($directory in @('examples','tests')) { Copy-Item -LiteralPath (Join-Path $sourceRoot $directory) -Destination $nodeRoot -Recurse }
    Push-Location $nodeRoot
    try {
        Invoke-SampleTestCommand 'npm.cmd' @('install','--package-lock=false','--ignore-scripts','--no-audit','--no-fund','--registry','https://registry.npmjs.org','--cache',(Join-Path $root 'npm-cache'))
        Invoke-SampleTestCommand 'node' @('--test','tests/samples.test.mjs')
    } finally { Pop-Location }

    $goRoot=Join-Path $run 'go'; [void][System.IO.Directory]::CreateDirectory($goRoot)
    Get-ChildItem -LiteralPath (Join-Path $sourceRoot 'go') | Copy-Item -Destination $goRoot -Recurse
    Invoke-SampleTestCommand $GoExecutable @('-C',$goRoot,'test','-mod=mod','-v','./...')

    $settings=Join-Path $run 'maven-settings.xml'
    $repository=[System.Security.SecurityElement]::Escape((Join-Path $root 'm2').Replace('\','/'))
    [System.IO.File]::WriteAllText($settings,"<settings xmlns=`"http://maven.apache.org/SETTINGS/1.2.0`"><localRepository>$repository</localRepository></settings>")
    $env:MAVEN_OPTS=$env:MAVEN_OPTS+' -Djava.io.tmpdir='+$env:TEMP.Replace('\','/')
    Invoke-SampleTestCommand $MavenCommand @('-B','-s',$settings,'-f',(Join-Path $sourceRoot 'java\pom.xml'),('-Dkingai.build.directory='+(Join-Path $run 'java-build').Replace('\','/')),'test')
    Write-Output "All sample suites passed. Test artifacts: $run"
} finally {
    foreach ($name in $names) { [Environment]::SetEnvironmentVariable($name,$previous[$name],'Process') }
}
