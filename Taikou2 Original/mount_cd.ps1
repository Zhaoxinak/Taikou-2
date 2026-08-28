param(
    [Parameter(Mandatory = $true)]
    [string]$IsoPath
)

$ErrorActionPreference = 'Stop'

try {
    $img = Get-DiskImage -ImagePath $IsoPath -ErrorAction SilentlyContinue
    if (-not $img -or -not $img.Attached) {
        Mount-DiskImage -ImagePath $IsoPath | Out-Null
    }
    exit 0
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
