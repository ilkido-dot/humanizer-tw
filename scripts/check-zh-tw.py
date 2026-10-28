#!/usr/bin/env python3
"""檢查文字是否符合台灣繁體中文的用字與標點慣例。

會抓四類問題：
  簡體字      例如「这」「们」，代表文字可能沒有轉換完全
  殘留字形    例如「着」「爲」「裏」，台灣不用的繁體字形（SKILL.md §32）
  標點        中文裡的彎引號、直引號和半形標點（SKILL.md §21）
  大陸用語    例如「視頻」「默認」，列出來讓人判斷（SKILL.md §31）

用法：
  python3 scripts/check-zh-tw.py 檔案.md [更多檔案 ...]
  python3 scripts/check-zh-tw.py - < 文字.txt
  python3 scripts/check-zh-tw.py --self-test

前三類算錯誤，有錯誤時以狀態碼 1 結束。大陸用語只是提醒，因為同一個詞換個
語境可能沒錯；加上 --strict 時也算錯誤。程式碼區塊、行內程式碼、網址和
hashtag 不檢查。只需要 Python 3，不用安裝任何套件。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# 只在簡體中文出現、在繁體中文裡從不正確的字。清單已用 OpenCC 的字典核對過，
# 排除了「后」「里」「干」這類在繁體裡也正確的字。
SIMPLIFIED_CHARS = frozenset(
    "与专业东丝两严个临为举义乌乐习书买乱争亏亚产亩亲亿仅从仑仓仪们众优会伞伟传伤伦体"
    "侠侣侦侧债倾偿储儿兑兰关兴养兽内冈册写军农冯冲决况冻净凉减凑凤凭凯击凿刘则刚创删"
    "别刹剂剑剧劝办务动劳势勋区医华协单卖卢卫却厅历压厌厕厢厨县参双发变叙叠号叹吓吕吗"
    "启吴员呜响哑哗唤喷团园围国图圆圣场坏块坚坛坝坟垄垒堕墙壮声壳处备复头夹夺奋奖妇妈"
    "娄娱婴孙学宁宝实宠审宪宫宽宾对寻导寿将尔尘尝层属岁岂岗岛岭峡币师帐带帮库应庙庞废"
    "开异弃张弯弹强归当录彻径忆忏忧怀态怜总恋恶恼悦悬惊惧惨惯愤戏战户扑执扩扫扬抚抛抢"
    "护报担拟拥拦拨择挡挣挤挥损换掷揽搁摄摆摇撑敌数斋断无旧时显晋晒晓晕暂术机杀杂权条"
    "来杨构枪标栏树样档桥梦检楼欢欧毁毕气汇汉汤沟没沧沪泪泻泽洁浅测济浏浑浓涛涨渐渔温"
    "湾湿溃滚满滤滨灭灯灵灾炉点烂烦烧烫热爱爷牵犹独狮狱猎猪献环现电画畅疗疯痒瘾盏盐监"
    "盖盘矫矿码砖础碍礼祸离积称稳穷窃窍窝竖笋笔签简类粮紧纠红纤约级纪纯纳纵纷纸线练组"
    "细织终绍经结绕绘给络绝统绣继绩续维绿缓编缘缩网罗罚罢职联聪肃肠肤肿胁胆胶脏脑脚脸"
    "舰艰艺节苏茧荡荣药莱获萝营蓝虏虑虚虽蚀蛮衔补袭装见观规视览觉触誉计订认讨让训议讯"
    "记讲许论设访证评识诉词译试诗诚话询该详语误说请诸读课谁调谈谢谦谱贝负贡财责贤败货"
    "质贩贪购贯贴贵贸费资赏赔赚赛赞赵赶趋跃践踪车轨转轮软轻载较辅辆辈辉输辞边达迁过运"
    "还这进远违连迟选递遗邮邻郑酱释针钟钢钱铁铜银链销锁锅错键长门闭问闲间闹闻阅阔队阳"
    "阴阵阶际陆陈险随隐难雾静页顶项顺须顾预领频题颜额风飞饭饮饰饱馆马驶验鱼鲜鸟鸡麦黄"
    "齐龙"
)

# 台灣不用的繁體字形 → 台灣標準字形（§32）
VARIANT_CHARS = {
    "着": "著",
    "爲": "為",
    "裏": "裡",
    "綫": "線",
    "衞": "衛",
    "峯": "峰",
    "羣": "群",
    "啓": "啟",
    "眞": "真",
    "衆": "眾",
    "僞": "偽",
    "麪": "麵",
    "牀": "床",
}

# 大陸用語 → (台灣用語, 是否要看語境)。要看語境的詞，在某些意思下是對的。（§31）
MAINLAND_TERMS = {
    "視頻": ("影片", False),
    "質量": ("品質", True),
    "信息": ("資訊、訊息", False),
    "軟件": ("軟體", False),
    "硬件": ("硬體", False),
    "網絡": ("網路", False),
    "互聯網": ("網路、網際網路", False),
    "人工智能": ("人工智慧", False),
    "算法": ("演算法", False),
    "數字化": ("數位化", False),
    "芯片": ("晶片", False),
    "內存": ("記憶體", False),
    "程序": ("程式", True),
    "代碼": ("程式碼", True),
    "用戶": ("使用者", True),
    "默認": ("預設", True),
    "通過": ("透過", True),
    "高清": ("高畫質", False),
    "鏈接": ("連結", False),
    "激活": ("啟用", False),
    "菜單": ("選單", True),
    "文檔": ("文件", False),
    "文件夾": ("資料夾", False),
    "數據庫": ("資料庫", False),
    "服務器": ("伺服器", False),
    "屏幕": ("螢幕", False),
    "打印": ("列印", False),
    "短信": ("簡訊", False),
    "項目": ("專案", True),
    "支持": ("支援", True),
    "營銷": ("行銷", False),
    "性價比": ("CP 值、價效比", False),
    "博主": ("部落客、創作者", False),
    "點贊": ("按讚", False),
    "評論區": ("留言區", False),
    "靠譜": ("可靠、靠得住", False),
    "小夥伴": ("朋友、大家", False),
    "種草": ("推坑、推薦", True),
    "乾貨": ("實用內容、重點", True),
}

# 剛好包含大陸用語、但其實是台灣正確用法的詞。落在這些詞裡面的命中不算。
TERM_EXCEPTIONS = {
    "算法": re.compile("演算法"),
    "內存": re.compile("內存在"),
}

CJK = r"㐀-䶿一-鿿"
CJK_OPEN = CJK + "「『（"
CJK_CLOSE = CJK + "」』）"
HALF_PUNCT = {",": "，", ";": "；", ":": "：", "?": "？", "!": "！", ".": "。"}

# 中文之間（或中文後面接行尾）的半形標點。句點後面接數字時是小數點，不算。
HALF_PUNCT_RE = re.compile(
    rf"(?<=[{CJK_CLOSE}])[,;:?!](?=\s*(?:[{CJK_OPEN}]|$))"
    rf"|(?<=[{CJK_CLOSE}])\.(?=\s*(?:[{CJK_OPEN}]|$))"
)
CURLY_QUOTE_RE = re.compile(rf"[“”‘’](?=[{CJK}])|(?<=[{CJK}])[“”‘’]")
STRAIGHT_QUOTE_RE = re.compile(rf'"(?=[{CJK}])|(?<=[{CJK}])"')

FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
HASHTAG_RE = re.compile(r"(?<![\w#])#(?=[^\s#])[^\s#]+")


@dataclass(frozen=True)
class Finding:
    line: int
    column: int
    kind: str
    text: str
    advice: str
    is_error: bool


def mask(text: str, pattern: re.Pattern[str]) -> str:
    """把不檢查的片段換成同長度的空白，欄位位置才不會跑掉。"""
    return pattern.sub(lambda match: " " * len(match.group(0)), text)


def check_line(line: str, number: int) -> list[Finding]:
    for pattern in (INLINE_CODE_RE, URL_RE, HASHTAG_RE):
        line = mask(line, pattern)
    findings: list[Finding] = []

    for column, char in enumerate(line, start=1):
        if char in SIMPLIFIED_CHARS:
            findings.append(Finding(number, column, "簡體字", char,
                                    "整段可能沒有轉換完全，請整段檢查", True))
        elif char in VARIANT_CHARS:
            findings.append(Finding(number, column, "殘留字形", char,
                                    f"改成「{VARIANT_CHARS[char]}」", True))

    for match in HALF_PUNCT_RE.finditer(line):
        mark = match.group(0)
        findings.append(Finding(number, match.start() + 1, "標點", mark,
                                f"中文裡改用全形的「{HALF_PUNCT[mark]}」", True))
    for pattern in (CURLY_QUOTE_RE, STRAIGHT_QUOTE_RE):
        for match in pattern.finditer(line):
            findings.append(Finding(number, match.start() + 1, "標點", match.group(0),
                                    "台灣的中文正文用「」和『』", True))

    for term, (suggestion, needs_context) in MAINLAND_TERMS.items():
        exception = TERM_EXCEPTIONS.get(term)
        excluded = [span.span() for span in exception.finditer(line)] if exception else []
        for match in re.finditer(re.escape(term), line):
            if any(start <= match.start() and match.end() <= end for start, end in excluded):
                continue
            advice = f"台灣通常說「{suggestion}」"
            if needs_context:
                advice += "；這個詞在某些意思下沒錯，請看語境"
            findings.append(Finding(number, match.start() + 1, "大陸用語", term,
                                    advice, False))

    return sorted(findings, key=lambda finding: finding.column)


def check_text(text: str) -> list[Finding]:
    findings: list[Finding] = []
    in_fence = False
    for number, line in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            findings.extend(check_line(line, number))
    return findings


def report(name: str, findings: list[Finding], strict: bool) -> int:
    errors = 0
    for finding in findings:
        failed = finding.is_error or strict
        errors += failed
        label = "錯誤" if failed else "提醒"
        print(f"{name}:{finding.line}:{finding.column}  {label}［{finding.kind}］"
              f"「{finding.text}」  {finding.advice}")
    return errors


SELF_TESTS = [
    # (文字, 應該抓到的類別, 是否應該完全沒有問題)
    ("先把舊水苔拿掉，再放進泡過水的新水苔。", set(), True),
    ("這款产品的说明还没更新。", {"簡體字"}, False),
    ("爲了安全着想，裏面的綫都換過了。", {"殘留字形"}, False),
    ("觀衆拿到的是僞造的票。", {"殘留字形"}, False),
    ("他說“這批苗況很好”,但其他人不同意。", {"標點"}, False),
    ('老闆說"下週到貨"。', {"標點"}, False),
    ("這個視頻默認是高清畫質。", {"大陸用語"}, False),
    ("推薦算法跑在新的芯片上。", {"大陸用語"}, False),
    ("這個演算法會推薦內容，他的體內存在抗體。", set(), True),
    ("棒球的重量約 0.145 公斤，網址是 https://example.com/a,b。", set(), True),
    ("在 `print(a,b)` 裡逗號是半形的。", set(), True),
    ("今天的貼文 #植物控 #視頻", set(), True),
    ("He said “hello” and left.", set(), True),
]


def self_test() -> int:
    failures = 0
    for text, expected_kinds, expect_clean in SELF_TESTS:
        findings = check_text(text)
        kinds = {finding.kind for finding in findings}
        ok = (not findings) if expect_clean else expected_kinds <= kinds
        if not ok:
            failures += 1
            print(f"失敗：{text!r} 預期 {sorted(expected_kinds) or '沒有問題'}，"
                  f"實際 {sorted(kinds) or '沒有問題'}")
    if failures:
        return 1
    print(f"check-zh-tw 自我測試通過（{len(SELF_TESTS)} 個案例）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="檢查文字是否符合台灣繁體中文的用字與標點慣例。")
    parser.add_argument("paths", nargs="*", help="要檢查的檔案；用 - 讀取標準輸入")
    parser.add_argument("--strict", action="store_true", help="大陸用語也算錯誤")
    parser.add_argument("--self-test", action="store_true", help="執行內建測試")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.paths:
        parser.error("請指定至少一個檔案，或用 - 讀取標準輸入")

    errors = 0
    for path in args.paths:
        if path == "-":
            name, text = "<stdin>", sys.stdin.read()
        else:
            try:
                name, text = path, Path(path).read_text(encoding="utf-8")
            except OSError as error:
                print(f"讀不到 {path}：{error}", file=sys.stderr)
                return 2
        errors += report(name, check_text(text), args.strict)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
