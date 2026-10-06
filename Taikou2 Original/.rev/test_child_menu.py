# -*- coding: utf8 -*-
"""test_child_menu.py —— M3c 桩的开发期自检 (不碰 exe, 只用占位 VA 装配+回读)"""
import child_menu as CM

M = lambda o: 0x54B600 + o
L = {'menu_ptr': M(0x5320), 'menu_code': M(0x5360), 'str_va': M(0x53D0),
     'pool': 0x53C000, 'bm': M(0x100), 'kid': M(0x2100), 'ring': M(0x5100),
     'name_buf': M(0x5600), 'slot_arr': M(0x5720), 'sub_ptr': M(0x5740),
     'act_ptr': M(0x5780), 'teach_ptr': M(0x57D0), 'tier_ptr': M(0x5800),
     'dec100': M(0x5530), 'giv': 0x549800, 'sur': 0x547C00, 'cap': 0x400,
     'c_menu': M(0x2040), 'c_panel': M(0x2038), 'c_push': M(0x203C),
     'c_notcity': M(0x2030), 'last_slot': M(0x2034), 'last_act': M(0x2018)}
L.update(CM.scratch_layout(M(0x5830)))

code, src = CM.build_hook(M(0x5860), L)
CM.selfcheck_hook(code, M(0x5860), L)
print('hook %dB selfcheck ok' % len(code))
code2, src2 = CM.build_foster(M(0x5A00), L)
CM.selfcheck_foster(code2, M(0x5A00), L)
print('foster %dB selfcheck ok' % len(code2))
print('strpool %dB dec100 %dB' % (len(CM.str_pool_bytes()), len(CM.dec100_bytes())))
print(' | '.join(CM.str_items()))
if __name__ == '__main__':
    import sys
    if '-v' in sys.argv:
        for i in CM._dis(code, M(0x5860)):
            print(' %08X  %-22s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
        print(' --- foster ---')
        for i in CM._dis(code2, M(0x5A00)):
            print(' %08X  %-22s %s %s' % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
