<# Open the existing Sydney Small lab through SSM. Creates no AWS resources. #>
[CmdletBinding()]
param(
    [ValidateSet('dev', 'staging')][string]$Environment = 'dev',
    [Parameter(Mandatory = $true)][ValidatePattern('^\d{12}$')][string]$ExpectedAccount,
    [string]$Profile = 'moodle-project',
    [string]$Python = 'python',
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $repoRoot $(if ($Environment -eq 'dev') { 'config/sydney.yaml' } else { 'config/sydney-staging.yaml' })
Push-Location $repoRoot
try {
    $configJson = & $Python -c 'import json, sys; from src.moodle_cloud import load_config; print(json.dumps(load_config(sys.argv[1])))' $configPath
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the lab configuration. Check Python, PyYAML and the YAML file.' }
    $labConfig = $configJson | ConvertFrom-Json
}
finally { Pop-Location }
if ($labConfig.environment -ne $Environment) { throw 'The YAML environment does not match the selected environment.' }
$region = $labConfig.region
$awsCommand = Get-Command aws -ErrorAction SilentlyContinue
$awsExecutable = if ($awsCommand) { $awsCommand.Source } else { 'C:\Program Files\Amazon\AWSCLIV2\aws.exe' }
if (-not (Test-Path -LiteralPath $awsExecutable)) { throw 'Install AWS CLI v2 and reopen PowerShell.' }
if (-not (Get-Command session-manager-plugin -ErrorAction SilentlyContinue)) {
    throw 'Install the AWS Session Manager plugin and reopen PowerShell.'
}

function Invoke-LabAws {
    param([string[]]$Arguments)
    $result = & $awsExecutable --profile $profile --region $region --no-cli-pager @Arguments --output json
    if ($LASTEXITCODE -ne 0) { throw "AWS command failed. If the session expired, authenticate the $Profile profile first." }
    return ($result | ConvertFrom-Json)
}

$identity = Invoke-LabAws -Arguments @('sts', 'get-caller-identity')
if ($identity.Account -ne $expectedAccount) { throw 'AWS account does not match the Sydney lab.' }
$name = "$($labConfig.project)-$Environment"
$inventory = Invoke-LabAws -Arguments @('ec2', 'describe-instances', '--filters', "Name=tag:Name,Values=$name", 'Name=instance-state-name,Values=running')
$instances = @($inventory.Reservations | ForEach-Object { $_.Instances } | Where-Object { $_ })
if ($instances.Count -ne 1) { throw "Expected exactly one running $name instance; found $($instances.Count). Check EC2 inventory." }
$instance = $instances[0].InstanceId
$nodes = Invoke-LabAws -Arguments @('ssm', 'describe-instance-information', '--filters', "Key=InstanceIds,Values=$instance")
if (@($nodes.InstanceInformationList | Where-Object { $_.PingStatus -eq 'Online' }).Count -ne 1) {
    throw 'The selected instance is not SSM Online. Check the instance, agent and network.'
}
Write-Host "Target: $name | $instance | $region | account $expectedAccount"
Write-Host 'SSM Online. Check application health separately with the Python CLI.'
if ($CheckOnly) { return }
if (Get-NetTCPConnection -State Listen -LocalPort 8080 -ErrorAction SilentlyContinue) {
    throw 'Local port 8080 is already in use. Stop the old tunnel/application before switching environments.'
}

$parametersFile = Join-Path ([IO.Path]::GetTempPath()) ('moodle-demo-' + [guid]::NewGuid().ToString('N') + '.json')
try {
    [IO.File]::WriteAllText($parametersFile, '{"portNumber":["8080"],"localPortNumber":["8080"]}', [Text.UTF8Encoding]::new($false))
    Write-Host "Keep this terminal open, then visit $($labConfig.wwwroot) in your browser. Ctrl+C closes the tunnel."
    & $awsExecutable --profile $profile --region $region ssm start-session --target $instance --document-name AWS-StartPortForwardingSession --parameters "file://$parametersFile"
    if ($LASTEXITCODE -ne 0) { throw 'SSM port forwarding ended with an error.' }
}
finally {
    if (Test-Path -LiteralPath $parametersFile) { Remove-Item -LiteralPath $parametersFile }
}
