# WSL への引き継ぎ書（n分都市化支援ツール実装）

最終更新: 2026-06-22 / 作成: Claude(Opus 4.8)

## なぜ WSL へ移行するか
Windows ネイティブでは codex が **OS サンドボックスを張れず、`-s workspace-write` でも実質 read-only** になりファイルを生成できなかった（唯一の回避策 `--dangerously-bypass-approvals-and-sandbox` は全ガードレール無効化のため Claude Code 側で自動ブロック）。
WSL(Linux) では codex のサンドボックス（Landlock）が機能し、**危険フラグなしの `-s workspace-write` で安全にファイル生成できる**ため、実装作業を WSL に移す。

## WSL 環境の状態（確認済 ✅）
| 項目 | 状態 |
|---|---|
| ディストロ | Ubuntu-22.04（WSL2、既定） |
| git | 2.34.1 |
| python3 | 3.10.12 |
| node / npm | v20.20.2 / 10.8.2 |
| codex | `/home/shin/.local/bin/codex`、**Logged in using ChatGPT** ✅ |
| ユーザー / HOME | `shin` / `/home/shin` |

※ Windows 側の codex 認証（`%USERPROFILE%\.codex`）と WSL 側（`~/.codex`）は別物。WSL 側は既にログイン済なので追加認証は不要。

## これまでの成果（Windows 側で完了）
- GitHub リポジトリ `https://github.com/shintaro-tanimoto/tosi-design`（公開）に push 済。コミット2件：
  1. `M0: リポジトリ初期化（要件定義書・plan・PROGRESS・.gitignore）`
  2. `docs: M0 進捗更新`
- リポジトリ同梱物：`要件定義書.html`（仕様、§6.7 で都市デザインの質レイヤ追加済）、`plan.md`（実装計画）、`PROGRESS.md`（進捗）、`.gitignore`。
- **著作権配慮**：`reference/`（モレノ著書全文テキスト）は `.gitignore` 除外で push していない → **clone すれば自動的にクリーン**（reference/ は含まれない）。

## WSL での継続手順

### 1. リポジトリを WSL ネイティブFSに clone（推奨）
`/mnt/c`（OneDrive 配下）は I/O が遅く・権限/サンドボックス相性が悪いので、Linux ホーム配下で作業する。
```bash
cd ~
git clone https://github.com/shintaro-tanimoto/tosi-design.git
cd tosi-design
git config user.name  "shintaro-tanimoto"
git config user.email "shintarotanigen@gmail.com"
```
> 要件定義書の原典が必要なら `要件定義書.html` は clone に含まれる。`reference/`（著書全文）は意図的に含めない（公開しない）。

### 2. push 用の認証（WSL git は GCM 無し）
いずれか：
- **Windows の Git Credential Manager を流用**（推奨・追加認証ほぼ不要）：
  ```bash
  git config --global credential.helper "/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe"
  ```
- もしくは PAT を使う（`git remote set-url origin https://<TOKEN>@github.com/shintaro-tanimoto/tosi-design.git`）。

### 3. Python 仮想環境
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
# requirements.txt 生成後:
pip install -r requirements.txt   # osmnx, geopandas, networkx, shapely, folium, plotly, pandas, numpy, pytest
```

### 4. codex で実装（危険フラグ不要）
プロンプトはファイルに書いて stdin で渡す（引用符問題回避）。
```bash
codex exec -C ~/tosi-design -s workspace-write -o /tmp/codex_last.txt - < /tmp/prompt.md
```
- `-s workspace-write`：ワークスペース内は書込可、外部は読取専用、ネット遮断（Linux サンドボックス）。
- 生成後は **Claude が diff をレビュー → `pytest` 実行 → git commit/push**。

## マイルストーン（plan.md と同じ）
- **M0b** スキャフォールド：`src/nmincity/`（config・NetworkBackend ABC・score 純関数・cli スタブ）＋ requirements/pyproject/README ＋ pytest 緑。
  - codex プロンプトは Windows 側 `C:\Users\shint\codex_prompts\m0b_scaffold.md` に作成済（内容は plan.md の M0b 仕様と同一）。WSL では `/mnt/c/Users/shint/codex_prompts/m0b_scaffold.md` で参照可。
- **M1** 機能A(MVP)：osmnx loader ＋ osmnx_backend(ego_graph 到達圏) ＋ reachability a(i,c) ＋ score S ＋ folium 地図 ＋ tests。
- **M2** 質レイヤ(§6.7)：walkability(要素A) ＋ chronotopia a(i,c,t)(要素B) ＋ 体験指標(要素C) ＋ Q(i)。
- **M3** 提案(機能B) ＋ 感度分析 ＋ S×Q 散布 ＋ 時間帯可視化。
- **M4(任意)** 機能C：Location-Allocation。

## 設計の肝（再掲）
計算バックエンドを `NetworkBackend`(ABC) で抽象化し、今は `OsmnxBackend`、将来 `ArcpyBackend`(ArcGIS Network Analyst) に差し替え可能にする。コア（score/quality/proposals）はバックエンド非依存。

## 進捗管理ルール（厳守）
各ステップ（codex 仕様→生成→検証→commit の前後）で **`PROGRESS.md` と セッションタスクを逐一更新**し、commit/push する。

## 未確定・要確認
- 対象 OSM 地区名（既定：取得が速い小さめの東京の地区。`--place` で変更可）。
- codex 既定モデルが「gpt5.5」相当か（必要なら `-m` 指定。今は既定で進行）。
