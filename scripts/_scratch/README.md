# scripts/_scratch — 一次性探针 / 实验脚本

> 破解过程中的 _probe_* / _scan_* / _disasm_* / 迭代枚举器等。
> **不要当权威接口**。可复跑、可对照，但不保证与最新结论一致。
>
> 根目录 scripts/ 只留：
> - *_ref.py — 自检断言（PASS = 结论仍成立）
> - _fdis.py / _lindis.py / _ins_index.py / _xref_reads.py / _string_pool_scan.py / _unpack_exe.py / _dumpfn.py — 核心工具
> - _emu_*.py — Unicorn 仿真
> - 命名产物脚本（diplomacy_strings.py / item_base_price.py / eal_assets.py 等）
> - *.json 数据产物
>
> 工作映像：_unpacked_mem.bin（2MB，gitignore，勿删）
