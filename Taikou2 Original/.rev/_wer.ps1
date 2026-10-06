[Console]::OutputEncoding=[Text.Encoding]::UTF8
$e = Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=(Get-Date).AddHours(-3)} -MaxEvents 500 -ErrorAction SilentlyContinue |
     Where-Object { $_.ProviderName -match 'Error|WER|Hang' }
if (-not $e) { 'no events'; exit }
$e | Select-Object -First 6 | ForEach-Object {
  '=== ' + $_.TimeCreated + ' [' + $_.ProviderName + ']'
  $_.Message
}
