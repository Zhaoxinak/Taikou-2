[Console]::OutputEncoding=[Text.Encoding]::UTF8
Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=(Get-Date).AddMinutes(-25)} -MaxEvents 300 -ErrorAction SilentlyContinue |
  Where-Object { $_.ProviderName -match 'Error|WER|Hang' } |
  ForEach-Object { $_.TimeCreated.ToString('HH:mm:ss') + ' [' + $_.ProviderName + '] ' + (($_.Message -split "`r?`n")[0]) }
