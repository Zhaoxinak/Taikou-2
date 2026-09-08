# -*- coding: utf-8 -*-
"""
导出 30 条店铺人格记录 → data/shops.json（供 src/core/shop.gd 加载）
==================================================================
权威：scripts/msgx_text_tables.json['S8_dialogue_30x12B']（已解析的 30×12B）
      布局见 scripts/shop_record_head_ref.py（续247 记录头）
      id→slot 表见 scripts/shop_npc_record_ref.py（续242 A5）

原版记录 30×12B @0x517850（运行时区，静态映像为 0，故取已解析的 S8 表）：
  +0x00 word name_key  人名/对话键 (1000+idx)
  +0x02 word shop_msg  商店对话 MSGX (700..728；#29 闇商人 = 0xffff)
  +0x04 byte job       职业码 0..11
  +0x05 byte province  所属国 0..48
  +0x06 byte rank      技艺等级 1..3
  +0x07 byte favor     店主关系值
  +0x08 word facility  设施状态
  +0x0a byte progress  进度计数
  +0x0b byte flags     事件旗

⚠️ /data/ 被 gitignore（导出产物），本脚本入版本控制以保证可复现。

运行：python scripts/export_shops_json.py
"""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# id→slot 字节表（续242 A5，30 项；第31字节 0x0b 为哨兵，shop_id≥30 不入店）
SLOTS = [0, 0, 0, 0, 0, 1, 2, 2, 2, 3, 3, 4, 4, 5, 5, 5,
         6, 6, 6, 7, 7, 8, 8, 8, 9, 9, 10, 10, 10, 12]


def main():
    src = os.path.join(_ROOT, 'scripts', 'msgx_text_tables.json')
    dst = os.path.join(_ROOT, 'data', 'shops.json')
    S8 = json.load(open(src, encoding='utf-8'))['S8_dialogue_30x12B']
    assert len(S8) == 30, f"期望 30 条，实得 {len(S8)}"

    out = []
    for i, r in enumerate(S8):
        rec = dict(
            id=i,
            name_key=r['talk_id'],      # +0x00 word
            shop_msg=r['shop_id'],      # +0x02 word（#29 = 65535/0xffff）
            job=r['b4'],                # +0x04 byte
            province=r['b5'],           # +0x05 byte
            rank=r['b6'],               # +0x06 byte
            favor=r['b7'],              # +0x07 byte
            facility=r['w8'],           # +0x08 word
            progress=r['ba'],           # +0x0a byte
            flags=r['bb'],              # +0x0b byte
            talk=r['talk'],             # MSGX 1000..1029
            shop=r['shop'],             # MSGX 700..728（#29 None）
            slot=SLOTS[i],
        )
        out.append(rec)

    # 自校验
    for rec in out:
        assert 0 <= rec['job'] < 12, f"job 越界 {rec}"
        assert 0 <= rec['rank'] <= 3, f"rank 越界 {rec}"
        assert 0 <= rec['province'] <= 48, f"province 越界 {rec}"
        assert (rec['shop_msg'] in range(700, 729)
                or rec['shop_msg'] == 65535), f"shop_msg 越界 {rec}"
        assert rec['slot'] == SLOTS[rec['id']]
    assert out[29]['shop_msg'] == 65535, "#29 应为 0xffff(闇商人)"

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    json.dump(out, open(dst, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f"[export_shops_json] 写入 {dst}，{len(out)} 条记录，自校验通过")


if __name__ == '__main__':
    main()
