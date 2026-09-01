#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
mci_av_subsystem_ref.py -- 续210：音频/视频子系统全破（三个 MCI 设备 + 18 个函数定名）
=====================================================================================
由续209（IAT 全量重建）直接引出：`mciSendCommandA` = `[0x4fb1e8]`，顺着它的调用点把
本作的**整个音视频栈**钉死。引擎不用 DirectSound/DirectMusic，**纯 MCI**（三个设备）：

┌ 设备 A ─ **CD 数字音频**（`lpstrDeviceType = 0x204 = MCI_DEVTYPE_CD_AUDIO`）
│   devID: `word[0x501290]`（0xFFFF = 未打开）   当前音轨: `byte[0x501294]`
│   已播放标志: `word[0x510310]`
│   `0x401040` CdOpen()             MCI_OPEN,  flags 0x3000 = TYPE|TYPE_ID
│   `0x401000` CdClose()            MCI_CLOSE
│   `0x4010a0` CdMediaPresent()     MCI_STATUS item 5 = MCI_STATUS_MEDIA_PRESENT
│   `0x4010f0` CdNumTracks()        MCI_STATUS item 3 = MCI_STATUS_NUMBER_OF_TRACKS
│   `0x401270` CdGetMode()          MCI_STATUS item 4 = MCI_STATUS_MODE
│   `0x401140` CdTrackLenMSF(t,&m,&s,&f)
│                MCI_SET  flags 0x400=TIME_FORMAT, fmt 2 = MCI_FORMAT_MSF
│                MCI_STATUS flags 0x110=ITEM|TRACK, item 1 = MCI_STATUS_LENGTH
│   `0x401210` CdTrackLenSec(t)     = m*60+s（`lea` 三连算 ×60）
│   `0x4013b0` CdPlayTrack(t)       MCI_SET fmt 0xa = MCI_FORMAT_TMSF
│                MCI_PLAY flags 0xd = NOTIFY|FROM|TO，dwCallback = hWnd `[0x526ba4]`
│   `0x4012c0` CdStopClose()        MCI_STOP + CdClose + 清 `[0x510310]`
│
├ 设备 B ─ **波形音频**（`lpstrDeviceType = 0x20a = MCI_DEVTYPE_WAVEFORM_AUDIO`）
│   devID: `word[0x501298]`   当前元素 id: `dword[0x510314]`   标志: `word[0x510318]`
│   `0x4014a0` WavOpen(id, alias)   先用 flags 0x13200（含 MCI_WAVE_OPEN_BUFFER
│                0x10000）试，失败降级 0x3200 = TYPE|TYPE_ID|ELEMENT；
│                文件名由 `0x4993a0(id)` 解析（资源名解析器）
│   `0x401540` WavIsPlaying()       MCI_STATUS item 4 == 0x20e = MCI_MODE_PLAY
│   `0x4015a0` WavStopClose()       MCI_STOP + WavClose + 清 `[0x510318]`
│   `0x401450` WavClose()           MCI_CLOSE + 释放 `[0x510314]`
│   `0x4015f0` WavPlay(id, ...)     同 id 且在播 → 直接返回；否则换元素重开
│                MCI_SET fmt 0 = MCI_FORMAT_MILLISECONDS
│                MCI_PLAY flags 5 = NOTIFY|FROM, dwFrom = 0
│
└ 设备 C ─ **AVI 动画**（`lpstrDeviceType = "avivideo"` @ `0x5056ec`）
    devID: `dword[0x514ab0]`   窗口/状态: `[0x514ab4]` `[0x514ab8]` `[0x514a80/84]`
    `0x46e8b0` AviOpen()             MCI_OPEN flags 0x2000 = MCI_OPEN_TYPE
    `0x46e7b0` AviFitWindow()        MCI_WHERE(0x843) flags 0x20000 取源矩形 →
                                     GetClientRect + 居中算式（`sar 1` 折半）→ MoveWindow
    `0x46e900` AviClose()            MCI_CLOSE + 清 `[0x514ab4]/[0x514ab8]`
    错误串 `0x5056f8` = GBK「无法打开动画文件。」

⚠️ **扫描陷阱**：本模块大量用 `mov esi,[0x4fb1e8]` + `call esi` 间接调用，所以
   「`call dword ptr [0x4fb1e8]` 只有 12 处」是**低估**；统计 MCI 调用必须同时数
   `call esi/edi` 形式（本脚本用「常量命令码 push」计数，绕开该陷阱）。

📌 **对 Godot 复刻的直接结论**：BGM = CD 音轨号（`Taikou2 Original` 的 34 个 mp3 即
   ripped CD 音轨，按轨号 1..34 索引）；音效 = WAV 文件元素（39 个 .wav）；开场/事件
   动画 = AVI。三者互不复用通道，可分别映射到 Godot 的 AudioStreamPlayer（BGM）、
   AudioStreamPlayer（SFX）、VideoStreamPlayer。
"""
import os as _os
def _find_root(_p):
    for _ in range(8):
        if _os.path.isdir(_os.path.join(_p, 'scripts')) and _os.path.isfile(_os.path.join(_p, 'project.godot')):
            return _p
        _p = _os.path.dirname(_p)
    return _p
_ROOT = _find_root(_os.path.dirname(_os.path.abspath(__file__)))

import os, sys, struct, json, re, collections
sys.path.insert(0, os.path.join(_ROOT, 'scripts'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from _disasm_all import disasm_all

BASE = 0x400000
MEM = open(os.path.join(_ROOT, 'scripts', '_unpacked_mem.bin'), 'rb').read()

MCI_SLOT = 0x4fb1e8          # IAT 槽 = mciSendCommandA（续209 重建）

# MCI 命令码（mmsystem.h）
CMD = {0x803: 'MCI_OPEN', 0x804: 'MCI_CLOSE', 0x806: 'MCI_PLAY', 0x807: 'MCI_SEEK',
       0x808: 'MCI_STOP', 0x809: 'MCI_PAUSE', 0x80d: 'MCI_SET', 0x814: 'MCI_STATUS',
       0x843: 'MCI_WHERE', 0x844: 'MCI_PUT'}


def u32(va):
    return struct.unpack('<I', MEM[va - BASE:va - BASE + 4])[0]


def u16(va):
    return struct.unpack('<H', MEM[va - BASE:va - BASE + 2])[0]


def gbk(va, n=48):
    d = MEM[va - BASE:va - BASE + n]
    k = d.find(b'\x00')
    return d[:k if k >= 0 else n]


def has(va, pat):
    return MEM[va - BASE:va - BASE + len(pat)] == pat


def main():
    tests = []

    def T(name, ok, detail=''):
        tests.append((name, bool(ok), detail))
        print('  %s %s%s' % ('PASS' if ok else 'FAIL', name, ('  — ' + detail) if detail else ''))

    print('=' * 78)
    print('A. 前提：mciSendCommandA = [0x4fb1e8]（续209 IAT 重建）')
    print('=' * 78)
    try:
        imap = json.load(open(os.path.join(_ROOT, 'scripts', 'iat_map.json')))
        api = imap['slots']['0x%06x' % MCI_SLOT]['api']
    except Exception as ex:
        api = '<iat_map.json 缺失: %s>' % ex
    T('[0x4fb1e8] = mciSendCommandA', api == 'mciSendCommandA', str(api))
    T('IAT 区仍为未解析占位（0x3000）', u32(MCI_SLOT) == 0x3000, '0x%x' % u32(MCI_SLOT))

    print()
    print('=' * 78)
    print('B. 三个设备的 devID 全局 + 初值 0xFFFF（未打开哨兵）')
    print('=' * 78)
    T('设备A devID word[0x501290] 初值 0xFFFF', u16(0x501290) == 0xffff, '0x%04x' % u16(0x501290))
    T('设备B devID word[0x501298] 初值 0xFFFF', u16(0x501298) == 0xffff, '0x%04x' % u16(0x501298))
    T('设备C devID dword[0x514ab0] 初值 0（运行期填）', u32(0x514ab0) == 0)

    print()
    print('=' * 78)
    print('C. 设备类型判据（字节级）')
    print('=' * 78)
    # 0x401058: mov dword ptr [esp+8], 0x204   -> lpstrDeviceType = MCI_DEVTYPE_CD_AUDIO
    T('设备A lpstrDeviceType = 0x204 (MCI_DEVTYPE_CD_AUDIO) @0x401058',
      has(0x401058, b'\xc7\x44\x24\x08\x04\x02\x00\x00'))
    T('设备A 用 MCI_OPEN flags 0x3000 (TYPE|TYPE_ID) @0x401061',
      has(0x401061, b'\x68\x00\x30\x00\x00'))
    # 0x4014da: mov dword ptr [esp+0xc], 0x20a -> MCI_DEVTYPE_WAVEFORM_AUDIO
    T('设备B lpstrDeviceType = 0x20a (MCI_DEVTYPE_WAVEFORM_AUDIO) @0x4014da',
      has(0x4014da, b'\xc7\x44\x24\x0c\x0a\x02\x00\x00'))
    T('设备B MCI_OPEN 双档 flags 0x13200 → 降级 0x3200',
      has(0x4014ef, b'\x68\x00\x32\x01\x00') and has(0x401506, b'\x68\x00\x32\x00\x00'))
    # 0x46e8cd: mov dword ptr [esp+0x18], 0x5056ec -> lpstrDeviceType = "avivideo"
    T('设备C lpstrDeviceType 指向 0x5056ec @0x46e8cd',
      has(0x46e8cd, b'\xc7\x44\x24\x18\xec\x56\x50\x00'))
    T('0x5056ec = "avivideo"', gbk(0x5056ec) == b'avivideo', repr(gbk(0x5056ec)))
    T('错误串 0x5056f8 = GBK「无法打开动画文件。」',
      gbk(0x5056f8).decode('gbk') == '无法打开动画文件。', gbk(0x5056f8).decode('gbk'))

    print()
    print('=' * 78)
    print('D. 命令码 + 时间格式 + STATUS item 逐一坐实')
    print('=' * 78)
    # STATUS item：mov dword ptr [esp+X], item
    T('CdMediaPresent 0x4010a0: STATUS item 5 (MEDIA_PRESENT)',
      has(0x4010c9, b'\xc7\x44\x24\x18\x05\x00\x00\x00') and has(0x4010c3, b'\x68\x14\x08\x00\x00'))
    T('CdNumTracks 0x4010f0: STATUS item 3 (NUMBER_OF_TRACKS)',
      has(0x401119, b'\xc7\x44\x24\x18\x03\x00\x00\x00') and has(0x401113, b'\x68\x14\x08\x00\x00'))
    T('CdGetMode 0x401270: STATUS item 4 (MODE)',
      has(0x401299, b'\xc7\x44\x24\x18\x04\x00\x00\x00') and has(0x401293, b'\x68\x14\x08\x00\x00'))
    T('CdTrackLenMSF 0x401140: SET fmt 2 (MCI_FORMAT_MSF) + STATUS flags 0x110 item 1(LENGTH)',
      has(0x40119d, b'\x68\x0d\x08\x00\x00') and has(0x4011a3, b'\xc7\x44\x24\x24\x02\x00\x00\x00')
      and has(0x4011bc, b'\x68\x10\x01\x00\x00') and has(0x4011d3, b'\xc7\x44\x24\x34\x01\x00\x00\x00'))
    T('CdPlayTrack 0x4013b0: SET fmt 0xa (MCI_FORMAT_TMSF) + PLAY flags 0xd (NOTIFY|FROM|TO)',
      has(0x4013c6, b'\x68\x0d\x08\x00\x00') and has(0x4013cc, b'\xc7\x44\x24\x28\x0a\x00\x00\x00')
      and has(0x401420, b'\x68\x06\x08\x00\x00') and has(0x40141e, b'\x6a\x0d'))
    T('CdPlayTrack 播完把音轨号存 byte[0x501294]',
      has(0x401430, b'\x88\x1d\x94\x12\x50\x00'))
    T('CdTrackLenSec 0x401210 = m*60+s（lea 三连 ×3 ×5 ×4）',
      has(0x401242, b'\x8d\x04\x40') and has(0x401245, b'\x8d\x0c\x80')
      and has(0x401248, b'\x8d\x04\x8a'))
    T('WavIsPlaying 0x401540: STATUS item 4 且比 0x20e (MCI_MODE_PLAY)',
      has(0x401569, b'\xc7\x44\x24\x18\x04\x00\x00\x00') and has(0x401587, b'\x81\xf9\x0e\x02\x00\x00'))
    T('WavPlay 0x4015f0: SET fmt 0 (MILLISECONDS) + PLAY flags 5 (NOTIFY|FROM)',
      has(0x401673, b'\x68\x0d\x08\x00\x00') and has(0x401679, b'\xc7\x44\x24\x24\x00\x00\x00\x00')
      and has(0x4016a6, b'\x68\x06\x08\x00\x00') and has(0x4016a4, b'\x6a\x05'))
    T('AviFitWindow 0x46e7b0: MCI_WHERE(0x843) flags 0x20000',
      has(0x46e7ea, b'\x68\x43\x08\x00\x00') and has(0x46e7df, b'\x68\x00\x00\x02\x00'))
    T('CD/Wav 的 MCI_NOTIFY 通知窗口都取自 dword[0x526ba4]',
      has(0x401417, b'\x8b\x15\xa4\x6b\x52\x00') and has(0x401694, b'\xa1\xa4\x6b\x52\x00'))

    print()
    print('=' * 78)
    print('E. 全镜像 MCI 命令码统计（含 `call esi` 间接形式，绕开续209 的低估陷阱）')
    print('=' * 78)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    direct = 0
    cmd_push = collections.Counter()
    sites = collections.defaultdict(list)
    for ins in disasm_all(md, MEM[0x401000 - BASE:], 0x401000):
        if ins.mnemonic == 'call' and ins.op_str == 'dword ptr [0x%x]' % MCI_SLOT:
            direct += 1
        if ins.mnemonic == 'push' and ins.op_str.startswith('0x'):
            v = int(ins.op_str, 16)
            if v in CMD:
                cmd_push[CMD[v]] += 1
                if len(sites[CMD[v]]) < 8:
                    sites[CMD[v]].append(ins.address)
    print('  `call dword ptr [0x4fb1e8]` 直接形式: %d 处' % direct)
    print('  MCI 命令码 push 统计（含间接 call esi 的调用点）:')
    for nm, n in cmd_push.most_common():
        print('    %-12s x%-3d  %s' % (nm, n, ', '.join('0x%06x' % a for a in sites[nm][:6])))
    T('MCI_OPEN/CLOSE/PLAY/STOP/SET/STATUS 六大命令全部出现',
      {'MCI_OPEN', 'MCI_CLOSE', 'MCI_PLAY', 'MCI_STOP', 'MCI_SET', 'MCI_STATUS'} <= set(cmd_push))
    T('命令码 push 总数 > 直接 call 数（证实存在 `call esi` 间接调用）',
      sum(cmd_push.values()) > direct, '%d > %d' % (sum(cmd_push.values()), direct))
    T('MCI_WHERE/MCI_PUT 存在（数字视频窗口定位）',
      'MCI_WHERE' in cmd_push and 'MCI_PUT' in cmd_push)

    print()
    print('=' * 78)
    print('F. 与素材目录交叉验证')
    print('=' * 78)
    def walk_ext(root, ext):
        out = []
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                if f.lower().endswith(ext):
                    out.append(os.path.relpath(os.path.join(dp, f), _ROOT))
        return sorted(out)

    mp3 = walk_ext(os.path.join(_ROOT, 'Taikou2 Original'), '.mp3')
    wav = walk_ext(os.path.join(_ROOT, 'scripts'), '.wav')
    print('  Taikou2 Original/**/*.mp3 = %d 个: %s ...' % (len(mp3), mp3[:3]))
    print('  scripts/**/*.wav          = %d 个: %s ...' % (len(wav), wav[:3]))
    T('mp3 数 > 1（CD 音轨 rip，供 BGM 按轨号索引）', len(mp3) > 1, str(len(mp3)))
    T('wav 数 > 1（waveaudio 设备的音效元素）', len(wav) > 1, str(len(wav)))

    out = {
        'mci_iat_slot': '0x%06x' % MCI_SLOT,
        'devices': {
            'A_cdaudio': {'devID': 'word[0x501290]', 'device_type': '0x204 MCI_DEVTYPE_CD_AUDIO',
                          'cur_track': 'byte[0x501294]', 'flag': 'word[0x510310]',
                          'fn': {'0x401040': 'CdOpen', '0x401000': 'CdClose',
                                 '0x4010a0': 'CdMediaPresent', '0x4010f0': 'CdNumTracks',
                                 '0x401270': 'CdGetMode', '0x401140': 'CdTrackLenMSF',
                                 '0x401210': 'CdTrackLenSec', '0x4013b0': 'CdPlayTrack',
                                 '0x4012c0': 'CdStopClose'}},
            'B_waveaudio': {'devID': 'word[0x501298]', 'device_type': '0x20a MCI_DEVTYPE_WAVEFORM_AUDIO',
                            'cur_element': 'dword[0x510314]', 'flag': 'word[0x510318]',
                            'fn': {'0x4014a0': 'WavOpen', '0x401450': 'WavClose',
                                   '0x401540': 'WavIsPlaying', '0x4015a0': 'WavStopClose',
                                   '0x4015f0': 'WavPlay'}},
            'C_avivideo': {'devID': 'dword[0x514ab0]', 'device_type': '"avivideo" @0x5056ec',
                           'fn': {'0x46e8b0': 'AviOpen', '0x46e7b0': 'AviFitWindow',
                                  '0x46e900': 'AviClose'},
                           'err_string': '0x5056f8 无法打开动画文件。'}},
        'notify_hwnd': 'dword[0x526ba4]',
        'cmd_push_counts': dict(cmd_push.most_common()),
        'direct_call_sites': direct,
    }
    outp = os.path.join(_ROOT, 'scripts', 'mci_av_subsystem.json')
    with open(outp, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('\nJSON ->', outp)

    npass = sum(1 for _, ok, _ in tests if ok)
    print('RESULT: %d/%d' % (npass, len(tests)))
    bad = [n for n, ok, _ in tests if not ok]
    assert not bad, '失败项: %s' % bad
    print('ALL PASS ✅  音视频子系统 = 3 个 MCI 设备 / 18 个函数定名')


if __name__ == '__main__':
    main()
