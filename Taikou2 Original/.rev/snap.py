"""
截图对比工具：启动指定 exe，等待若干秒后截全屏存为 PNG，然后结束进程。
用 PowerShell 的 System.Drawing 抓屏（比 GDI 的 GetDIBits 稳，不会拖垮被调试进程）。

用法:
    python .rev/snap.py <exe> <等待秒数> <输出png>
"""
import os
import subprocess
import sys
import time
import tempfile

PS = r'''
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save($args[0], [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output ("saved " + $args[0])
'''


def snap(out_png):
    ps = os.path.join(tempfile.gettempdir(), '_snap.ps1')
    open(ps, 'w', encoding='utf-8').write(PS)
    r = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                        '-File', ps, out_png],
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip() or r.stderr.strip()


def main():
    exe = sys.argv[1]
    wait = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        os.path.dirname(exe), '.rev', 'snap.png')

    p = subprocess.Popen([exe], cwd=os.path.dirname(exe))
    print('启动 %s pid=%d，等待 %.0f 秒...' % (os.path.basename(exe), p.pid, wait))
    time.sleep(wait)
    alive = p.poll() is None
    print('进程存活:', alive, '退出码:', p.returncode)
    print(snap(out))
    print('截图 ->', out)
    try:
        p.terminate()
    except Exception:
        pass


if __name__ == '__main__':
    main()
