#!/usr/bin/env python3
"""檢查 Humanizer-tw 的套件檔案，不需要安裝任何套件。

改寫自英文原版 blader/humanizer 的 scripts/validate-package.py（MIT）。
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "humanizer-tw"
# SKILL.md 每次使用都會被完整讀取，所以限制篇幅。中文沒有空格分詞，用字元數計算。
MAX_SKILL_CHARACTERS = 15000


def read_package_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"讀不到 {path.relative_to(ROOT)}：{error}")


def read_json(path: Path) -> dict:
    try:
        return json.loads(read_package_file(path))
    except json.JSONDecodeError as error:
        raise SystemExit(f"修正 {path.relative_to(ROOT)} 的 JSON：{error}")


def require_match(match: re.Match[str] | None, message: str) -> re.Match[str]:
    if match is None:
        raise SystemExit(message)
    return match


SKILL_PATH = ROOT / "SKILL.md"
SKILL = read_package_file(SKILL_PATH)
README = read_package_file(ROOT / "README.md")
CHANGELOG = read_package_file(ROOT / "CHANGELOG.md")
PLUGIN = read_json(ROOT / ".claude-plugin" / "plugin.json")
MARKETPLACE = read_json(ROOT / ".claude-plugin" / "marketplace.json")
CURSOR_PLUGIN = read_json(ROOT / ".cursor-plugin" / "plugin.json")

yaml_metadata = require_match(
    re.match(r"\A---\n(.*?)\n---\n", SKILL, re.DOTALL),
    "SKILL.md 開頭必須是 YAML 中繼資料",
).group(1)

for unsupported_field in ("version:", "compatibility:", "allowed-tools:"):
    if re.search(rf"(?m)^{re.escape(unsupported_field)}", yaml_metadata):
        raise SystemExit(f"移除不支援的 YAML 欄位：{unsupported_field[:-1]}")

skill_name = require_match(
    re.search(r"(?m)^name:\s*(\S+)\s*$", yaml_metadata),
    "在 SKILL.md 加上 name",
).group(1)
if skill_name != SKILL_NAME:
    raise SystemExit(f"SKILL.md 的 name 必須是 {SKILL_NAME}")
for manifest, label in ((PLUGIN, ".claude-plugin/plugin.json"),
                        (CURSOR_PLUGIN, ".cursor-plugin/plugin.json")):
    if manifest.get("name") != SKILL_NAME:
        raise SystemExit(f"{label} 的 name 必須是 {SKILL_NAME}")
if [plugin.get("name") for plugin in MARKETPLACE.get("plugins", [])] != [SKILL_NAME]:
    raise SystemExit(f"marketplace.json 必須只列出 {SKILL_NAME} 一個 plugin")

skill_version = require_match(
    re.search(r'(?m)^\s+version:\s*["\']?([0-9]+\.[0-9]+\.[0-9]+)["\']?\s*$', yaml_metadata),
    "在 SKILL.md 的 metadata.version 寫上三段式版本號",
).group(1)
changelog_version = require_match(
    re.search(r"(?m)^## ([0-9]+\.[0-9]+\.[0-9]+)$", CHANGELOG),
    "在 CHANGELOG.md 加上版本標題",
).group(1)
package_versions = {
    skill_version,
    changelog_version,
    str(PLUGIN.get("version", "")),
    str(CURSOR_PLUGIN.get("version", "")),
}
if len(package_versions) != 1:
    raise SystemExit(f"所有檔案要用同一個版本號：{sorted(package_versions)}")

skill_files = {path.relative_to(ROOT) for path in ROOT.rglob("SKILL.md")}
if SKILL_PATH.is_symlink() or skill_files != {Path("SKILL.md")}:
    raise SystemExit("只保留一份放在 repo 根目錄的 SKILL.md")
if PLUGIN.get("skills") != ["./"]:
    raise SystemExit("Claude plugin 的 skills 要指向 repo 根目錄")
if "skills" in CURSOR_PLUGIN:
    raise SystemExit("Cursor plugin 不要寫 skills，讓它讀根目錄的 SKILL.md")

skill_description = "".join(
    line.strip()
    for line in require_match(
        re.search(r"(?m)^description: \|\n((?:  .*\n)+)", yaml_metadata + "\n"),
        "SKILL.md 的 description 要寫成縮排區塊",
    ).group(1).splitlines()
)
if len(skill_description) > 1024:
    raise SystemExit(f"description 最多 1024 字元，現在是 {len(skill_description)}")
package_descriptions = {
    str(PLUGIN.get("description", "")),
    str(CURSOR_PLUGIN.get("description", "")),
    *(str(plugin.get("description", "")) for plugin in MARKETPLACE.get("plugins", [])),
}
if len(package_descriptions) != 1 or not skill_description.startswith(
    next(iter(package_descriptions))
):
    raise SystemExit(
        "每個 plugin 設定檔的 description 都要用 SKILL.md description 的第一句："
        f"{sorted(package_descriptions)}"
    )

skill_patterns = dict(
    (int(number), name)
    for number, name in re.findall(r"(?m)^### ([0-9]+)\. (.+)$", SKILL)
)
pattern_numbers = list(skill_patterns)
pattern_count = len(pattern_numbers)
if pattern_count == 0 or pattern_numbers != list(range(1, pattern_count + 1)):
    raise SystemExit(f"SKILL.md 的模式要從 1 開始連續編號：{pattern_numbers}")

readme_patterns = dict(
    (int(number), name)
    for number, name in re.findall(r"(?m)^\| ([0-9]+) \| \*\*(.+?)\*\*", README)
)
if sorted(readme_patterns) != pattern_numbers:
    raise SystemExit(
        f"README 的對照表要列出模式 1 到 {pattern_count}，每個一次：{sorted(readme_patterns)}"
    )
renamed = [
    f"{number}：{readme_patterns[number]!r} 應該是 {name!r}"
    for number, name in skill_patterns.items()
    if readme_patterns[number] != name
]
if renamed:
    raise SystemExit("README 的模式名稱要和 SKILL.md 一致：" + "；".join(renamed))
if f"## {pattern_count} 個模式" not in README:
    raise SystemExit(f"README 的模式章節標題要是「{pattern_count} 個模式」")

# 重新編號後，§ 參照可能指錯或指向不存在的模式。CHANGELOG.md 保留各版本當時的編號，所以只檢查 SKILL.md。
skill_references = sorted({int(number) for number in re.findall(r"§([0-9]+)", SKILL)})
missing_patterns = [number for number in skill_references if not 1 <= number <= pattern_count]
if missing_patterns:
    raise SystemExit(f"SKILL.md 的 § 參照要指向 1 到 {pattern_count}：{missing_patterns}")

skill_characters = len(re.sub(r"\s", "", SKILL))
if skill_characters > MAX_SKILL_CHARACTERS:
    raise SystemExit(
        f"SKILL.md 最多 {MAX_SKILL_CHARACTERS:,} 個字元（不含空白），現在是 {skill_characters:,}"
    )

print(f"Humanizer-tw 套件 v{skill_version} 檢查通過（{pattern_count} 個模式，{skill_characters:,} 字元）")
