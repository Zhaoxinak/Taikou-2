[Console]::OutputEncoding=[Text.Encoding]::UTF8
Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=(Get-Date).AddMinutes(-25); Level=2} -MaxEvents 50 -ErrorAction SilentlyContinue |
  Where-Object { $_.Message -match 'TAIK' } |
  ForEach-Object { $_.TimeCreated.ToString('HH:mm:ss'); $_.Message }
