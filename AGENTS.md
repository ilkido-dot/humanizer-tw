# 給 AI 代理的說明

這份文件說明怎麼修改 Humanizer-tw，而不會弄壞它的套件或提示詞。

## 這個 repo 是什麼

Humanizer-tw 是用 Markdown 寫的 agent skill，是英文原版 [blader/humanizer](https://github.com/blader/humanizer) 的台灣繁體中文版。`SKILL.md` 是代理讀取的提示詞。這個 repo 沒有建置步驟。

讓 skill 保持通用。不要寫出只適用於一兩種代理工具的指示。

## 主要檔案

- `SKILL.md` 是唯一的 skill 檔案，也是所有內容的依據。裡面有通用的 YAML 中繼資料、AI 文字為什麼會這樣的說明，以及分成八組、依強度和頻率排序的編號模式。
- `README.md` 說明安裝、使用方式和模式。
- `CHANGELOG.md` 放版本紀錄，最新的在最上面。舊紀錄保留當時的模式編號。
- `.claude-plugin/plugin.json` 描述 Claude plugin，並讓它的 skill 載入器指向根目錄的 `SKILL.md`。
- `.claude-plugin/marketplace.json` 讓使用者把這個 repo 加成 Claude marketplace。
- `.cursor-plugin/plugin.json` 描述 Cursor plugin。不要寫 `skills` 路徑，讓 Cursor 讀根目錄的 `SKILL.md`。
- `agents/openai.yaml` 放 OpenAI 相容代理的顯示名稱、簡短描述和預設提示。
- `scripts/validate-package.py` 檢查套件檔案和共用的值。
- `scripts/check-zh-tw.py` 檢查文字裡的簡體字、殘留字形、半形標點和大陸用語。

## 修改規則

`SKILL.md` 和 `README.md` 要保持一致。

- **和英文原版的對應：** §1 到 §26 與英文原版同號。同步英文原版的更新時，維持這個對應；英文原版新增的模式，加在 §26 之後、G 組之前，並把後面的編號往後移。
- **模式：** 模式從 1 開始連續編號，最強、最常見的在前面。新的痕跡只有在沒有任何現有模式涵蓋時，才成為新模式；能併入現有模式就併入。新增、刪除或重新編號模式時，要更新 README 的對照表、README 的章節標題「N 個模式」，以及每一個 § 參照。驗證腳本會從標題算出模式數量，並檢查 README 的模式名稱和標題一致。
- **版本：** `SKILL.md` 的 `metadata.version`、`CHANGELOG.md` 的第一個版本標題、`.claude-plugin/plugin.json` 和 `.cursor-plugin/plugin.json` 要用同一個版本號。不要在 skill 的最上層加 `version` 欄位。
- **相容性：** 安裝和使用說明對所有代理保持中立。Claude Code、Cursor、Codex 這些名字是例子，不是限制。
- **描述：** 每個 plugin 設定檔的描述，都用 `SKILL.md` description 的第一句。
- **篇幅：** `SKILL.md` 每次使用都會被完整讀取。驗證腳本限制它最多 15,000 個字元（不含空白）；增加字數的修改要值得那些字。
- **紀錄：** 任何行為改變或不明顯的修正，都在 `CHANGELOG.md` 加一則簡短紀錄。
- **檢查：** 發布前執行 `python3 scripts/validate-package.py`、`python3 scripts/check-zh-tw.py --self-test`、`npx skills add . --list` 和 `claude plugin validate .`。

## 寫作風格

程式註解、提示詞、文件、描述、驗證訊息和進度回報，都用台灣繁體中文和白話寫。

- 先講重點。
- 用常見的詞和主動語態。
- 句子和段落都要短。
- 同一個東西用同一個名稱。
- 要求用「必須」或「要」。
- 有幫助時才用標題、清單和表格。
- 刪掉重複或不需要的字。
- 少用縮寫，並解釋技術名詞。
- 避免雙重否定。
- 保留精確的識別名稱、指令、路徑、結構欄位、引文、被觀察的詞句和會影響行為的範例。
- 保留完整的技術意思。

## 修改 skill

- 讓 YAML 中繼資料保持有效。
- 中繼資料下面的提示詞就是產品本身。
- 寧可用一條簡短清楚的指示，也不要再加一個例外或重複的說明。
- `SKILL.md` 本身含有刻意的錯誤範例（例如 §21 的引號、§31 和 §32 的用字），所以不要用 `check-zh-tw.py` 檢查 `SKILL.md`。
