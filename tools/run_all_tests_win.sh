#!/bin/bash
# 全量无头测试跑批（Windows / Git Bash 适配版）
# 逐个跑 tools/_test_*.gd，每个最多 40s，结果汇总到 tests_report.txt
# 背景：本机 --script 模式曾被误判"主循环失效"，实测可用（需非沙箱运行）。
#       仍保留"后台启动 + 定时 taskkill"兜底，以防个别测试回退主场景卡死。
cd "F:/Games/Taikou 2" || exit 1
GODOT="F:/Games/Taikou 2/Godot_v4.7.1/Godot_v4.7.1-stable_win64_console.exe"
OUT="F:/Games/Taikou 2/tests_report.txt"
EXE_NAME="Godot_v4.7.1-stable_win64_console.exe"
: > "$OUT"

for f in tools/_test_*.gd; do
	name=$(basename "$f" .gd)
	# 强制清理上一轮的残留进程
	taskkill //F //IM "$EXE_NAME" >/dev/null 2>&1
	sleep 0.3
	tmp="/tmp/_t_$name.txt"
	( "$GODOT" --headless --script "res://$f" > "$tmp" 2>&1 & )
	# 最多等 40s
	for i in $(seq 1 40); do
		if ! tasklist //IM "$EXE_NAME" >/dev/null 2>&1; then break; fi
		sleep 1
	done
	# 超时仍未退出则强杀
	taskkill //F //IM "$EXE_NAME" >/dev/null 2>&1
	sleep 0.3
	# 判定：优先找汇总行，找不到则取末行实绩；单独标出 FAIL/Error
	summary=$(grep -viE "Unicode parsing error|Unexpected NUL" "$tmp" \
		| grep -E "ALL PASS|FAILURES|RESULT:|PASS / |checks passed|pass=|TEST:|Compile Error|Parse Error|全部通过|全链路通过|校验失败|FAIL" \
		| head -3 | tr '\n' ' ')
	if [ -z "$summary" ]; then
		summary="(无汇总行) 末行: $(grep -viE 'Unicode parsing error|Unexpected NUL' "$tmp" | tail -n 1 | cut -c1-100)"
	fi
	nfail=$(grep -viE "Unicode parsing error|Unexpected NUL" "$tmp" | grep -cE "\[FAIL\]|  FAIL |FAILURES|Compile Error|Parse Error|校验失败")
	line="[$nfail 失败迹象] $summary"
	echo "$name :: $line" >> "$OUT"
done
taskkill //F //IM "$EXE_NAME" >/dev/null 2>&1
echo "=== BATCH DONE ===" >> "$OUT"
