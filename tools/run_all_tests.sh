#!/bin/zsh
# 全量无头测试跑批：逐个跑 tools/_test_*.gd，每个最多 18s，结果汇总到 tests_report.txt
# 用法：zsh tools/run_all_tests.sh
# 背景：本机 macOS 无 timeout 命令；Godot --script 失败时会回退跑主场景（永不退出），
#       故必须后台启动 + 定时 pkill。
cd "/Users/ts/Downloads/Taikou 2" || exit 1
GODOT="/Users/ts/Downloads/Taikou 2/Godot/Godot.app/Contents/MacOS/Godot"
OUT="/Users/ts/Downloads/Taikou 2/tests_report.txt"
: > "$OUT"

for f in tools/_test_*.gd; do
	name=$(basename "$f" .gd)
	pkill -f "Godot.app/Contents/MacOS/Godot" 2>/dev/null
	sleep 0.3
	tmp="/tmp/_t_$name.txt"
	("$GODOT" --path "/Users/ts/Downloads/Taikou 2" --headless --script "res://$f" > "$tmp" 2>&1 &)
	sleep 15
	pkill -f "Godot.app/Contents/MacOS/Godot" 2>/dev/null
	sleep 0.3
	# 判定：优先找汇总行（各测试格式不一），找不到则取末尾实绩行，并单独标出 FAIL/Error
	summary=$(grep -viE "Unicode parsing error|Unexpected NUL" "$tmp" \
		| grep -E "ALL PASS|FAILURES|RESULT:|PASS / |checks passed|pass=|TEST:|Compile Error|Parse Error" \
		| head -3 | tr '\n' ' ')
	if [ -z "$summary" ]; then
		summary="(无汇总行) 末行: $(grep -viE 'Unicode parsing error|Unexpected NUL' "$tmp" | tail -n 1 | cut -c1-90)"
	fi
	nfail=$(grep -viE "Unicode parsing error|Unexpected NUL" "$tmp" | grep -cE "\[FAIL\]|  FAIL |FAILURES|Compile Error|Parse Error")
	line="[$nfail 失败迹象] $summary"
	echo "$name :: $line" >> "$OUT"
done
pkill -f "Godot.app/Contents/MacOS/Godot" 2>/dev/null
echo "=== BATCH DONE ===" >> "$OUT"
