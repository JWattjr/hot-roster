$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$approval=Get-Content -LiteralPath '.secrets/deposit-approval.json' | ConvertFrom-Json
if($approval.approvedTotalWei -ne '42'){throw 'Owner approval for 42 wei is required.'}
$proof=Get-Content -LiteralPath 'deploy/proof.json' | ConvertFrom-Json
$amounts=@('10','10','12','10')
$journalPath=Join-Path (Get-Location) 'deploy/funding.json'
$journal=if(Test-Path -LiteralPath $journalPath){Get-Content -LiteralPath $journalPath | ConvertFrom-Json -AsHashtable}else{@{approvedTotalWei='42';transfers=@{}}}
$previousOptions=$env:NODE_OPTIONS
try {
 $env:NODE_OPTIONS=($previousOptions+' --import=./scripts/explicit-fees.mjs').Trim()
 for($i=0;$i -lt 4;$i++){
  $key=[string]$i
  if($journal.transfers.ContainsKey($key)){continue}
  $wallet=$proof.demoPlayers[$i].wallet
  $ErrorActionPreference='Continue'
  $output=& genlayer.cmd account send $wallet $amounts[$i] --account moment-grid-studionet --network studionet 2>&1
  $ErrorActionPreference='Stop'
  $output | Write-Output
  if($LASTEXITCODE -ne 0){throw 'Funding command failed; inspect output before retrying.'}
  $hash=[regex]::Matches(($output -join "`n"),'0x[0-9a-fA-F]{64}') | Select-Object -Last 1 -ExpandProperty Value
  if(!$hash){throw 'Funding output lacked a durable transaction hash; do not repeat blindly.'}
  $journal.transfers[$key]=@{wallet=$wallet;wei=$amounts[$i];hash=$hash}
  $journal | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $journalPath
 }
} finally {$env:NODE_OPTIONS=$previousOptions}
