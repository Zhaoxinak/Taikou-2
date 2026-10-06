[Console]::OutputEncoding=[Text.Encoding]::UTF8
Get-ChildItem 'C:\ProgramData\Microsoft\Windows\WER\ReportArchive','C:\ProgramData\Microsoft\Windows\WER\ReportQueue' -Filter '*TAIK*' -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 8 |
  ForEach-Object { $_.LastWriteTime.ToString('MM-dd HH:mm:ss') + '  ' + $_.Name.Substring(0,50) }
'--- events (last 150 min, TAIK) ---'
Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=(Get-Date).AddMinutes(-150)} -MaxEvents 400 -ErrorAction SilentlyContinue |
  Where-Object { $_.Message -match 'TAIK' } |
  ForEach-Object {
    $lines = $_.Message -split "`r?`n"
    $app  = ($lines | Where-Object { $_ -match 'application name' } | Select-Object -First 1)
    $off  = ($lines | Where-Object { $_ -match 'offset|Fault offset' } | Select-Object -First 1)
    $mod  = ($lines | Where-Object { $_ -match 'module name' } | Select-Object -First 1)
    $_.TimeCreated.ToString('MM-dd HH:mm:ss') + ' [' + $_.ProviderName + '] ' + $app + ' ; ' + $mod + ' ; ' + $off
  }
