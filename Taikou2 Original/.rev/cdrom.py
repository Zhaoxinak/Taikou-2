"""检查/挂载虚拟光驱（游戏需要 CD 检测才能启动）。结果打印到 stdout。"""
import subprocess
import sys

ISO = r"F:\Games\Taikou 2\Taikou2 Original\taikou2_cd.iso"
PS = r'''
$ErrorActionPreference = 'Continue'
"=== CDROM ==="
Get-CimInstance Win32_CDROM | ForEach-Object { "DRIVE=" + $_.Drive + " LOADED=" + $_.MediaLoaded }
"=== DiskImage before ==="
try { $i = Get-DiskImage -ImagePath "%(iso)s" -ErrorAction Stop; "Attached=" + $i.Attached }
catch { "query failed: " + $_.Exception.Message }
"=== Mount ==="
try { Mount-DiskImage -ImagePath "%(iso)s" -StorageType ISO -Access Read -ErrorAction Stop; "mount ok" }
catch { "mount FAILED: " + $_.Exception.Message }
Start-Sleep -Seconds 2
"=== DiskImage after ==="
try { $i2 = Get-DiskImage -ImagePath "%(iso)s" -ErrorAction Stop; "Attached=" + $i2.Attached }
catch { "verify failed" }
''' % {"iso": ISO}


def main():
    cmd = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", PS]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=120)
    print("rc =", r.returncode)
    print(r.stdout)
    if r.stderr.strip():
        print("STDERR:", r.stderr.strip()[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
