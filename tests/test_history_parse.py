# -*- coding: utf-8 -*-
"""测试历史文案解析"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ui.history_dialog import HistoryDialog, _ENTRY_RE

# 模拟一个文案备份文件内容
SAMPLE = """---- [10:23:45] 早安 ----
26℃晴好天，东南风轻拂，小青喊你元气满满！☀️
#早安理工# #每日话题#

---- [22:15:30] 晚安 ----
晴暖26℃，晚风轻轻，小青祝你晚安呀～🌙
#晚安理工# #每日话题#

---- [15:00:00] 书籍 ----
《被讨厌的勇气》——同学们好，我是小青！
#小青超推荐# #每日话题# #大学生书单#
"""

print("=== 测试正则解析 ===")
matches = list(_ENTRY_RE.finditer(SAMPLE))
print(f"找到 {len(matches)} 条 entry")
for i, m in enumerate(matches, 1):
    print(f"\n--- 第 {i} 条 ---")
    print(f"  time: {m.group(1).strip()}")
    print(f"  type: {m.group(2).strip()}")
    print(f"  body (first 60): {m.group(3)[:60].strip()}")

assert len(matches) == 3, f"应该解析出 3 条，实际 {len(matches)}"
assert matches[0].group(2).strip() == "早安"
assert matches[1].group(2).strip() == "晚安"
assert matches[2].group(2).strip() == "书籍"
print("\n🎉 正则解析测试通过！")
