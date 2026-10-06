"""
检查游戏崩溃后的内存埋点标记。
用法: python .rev/check_markers.py [exe路径]

埋点位置:
  0x54B674 = 'D' (日推进内层 0x4A0E47)
  0x54B675 = 'E' (日推进外层 0x4A0D50)
  0x54B676 = 'F' (游戏入口 0x4F44B0)

如果某个位置的值为 0xFF, 说明对应的埋点被触发过。
"""
import sys
import pefile
import struct

EXE = sys.argv[1] if len(sys.argv) > 1 else r'F:\Games\Taikou 2\Taikou2 Original\TAIK2W95_big.exe'

pe = pefile.PE(EXE)

markers = [
    (0x54B674, 'D', '日推进内层 @0x4A0E47'),
    (0x54B675, 'E', '日推进外层 @0x4A0D50'),
    (0x54B676, 'F', '游戏入口 @0x4F44B0'),
]

print('检查内存埋点标记:')
print('=' * 60)
for va, name, desc in markers:
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    data = pe.get_data(rva, 1)
    value = data[0]
    status = '✓ 已触发' if value == 0xFF else '✗ 未触发'
    print(f'  [{name}] 0x{va:08X} = 0x{value:02X}  {status}')
    print(f'       {desc}')
print('=' * 60)

# 判断崩溃位置
fired = [name for va, name, desc in markers if pe.get_data(va - pe.OPTIONAL_HEADER.ImageBase, 1)[0] == 0xFF]
if not fired:
    print('\n结论: 没有任何埋点被触发。')
    print('可能原因:')
    print('  1. 游戏在到达入口(0x4F44B0)之前就崩溃了')
    print('  2. 埋点代码本身有问题')
    print('  3. 游戏运行的是其他 exe 文件')
elif 'F' in fired and 'E' not in fired:
    print('\n结论: 游戏入口被触发, 但日推进外层未被触发。')
    print('崩溃发生在: 启动 → 日推进之间')
elif 'E' in fired and 'D' not in fired:
    print('\n结论: 日推进外层被触发, 但内层未被触发。')
    print('崩溃发生在: 0x4A0D50 → 0x4A0E47 之间')
elif 'D' in fired:
    print('\n结论: 日推进内层被触发。')
    print('崩溃发生在: 0x4A0E47 之后的某个地方')
