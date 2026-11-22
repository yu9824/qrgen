# Technology Stack

## Architecture

純 Python のライブラリ (src レイアウト) と、それを呼ぶ CLI
(`__main__.py`)。依存は最小に保ち、重いものは optional extra に分ける。

## Core Technologies

- **Language**: Python >= 3.10 (CI は 3.10〜3.14 で回す)。サポートの切れた
  版は下限から外す
- **Build**: setuptools + setuptools_scm (>= 8)。バージョンは git タグ
  (`vX.Y.Z`) から決まる。`__version__` はインストール済みのメタデータから
  `importlib.metadata.version()` で読み、version file (`_version.py`) は
  作らない
- **開発環境**: conda 環境 `work` (`environment.yml`)。Dev Container では
  イメージに焼き込み済みで、自分自身は editable install

## Dependencies

- 実行時の依存は segno (QR の生成。純 Python で、それ自体は依存なし) だけ。
  通信する依存・依存の多いものは入れない
- extras: `test` (pytest)、`dev` (build)、`optional` (colorlog)、
  `camera` (opencv-python。QR の読み取り)、`docs` (Sphinx 一式)
- `opencv-python` は他の OpenCV の wheel (`-headless`, `-contrib`) と同じ
  環境に入れられない
- optional な依存は無くても import が通るようにする (structure.md 参照)
- 下限は「動作を確認した版」の意味で、Dependabot も新版を許容できる限り
  上げない (`versioning-strategy: increase-if-necessary`)

## Development Standards

### Type Safety
- 型ヒントを付け、mypy (`mypy.ini`) を通す
- 下限 (`requires-python`) の Python で動く書き方にする。それより新しい
  typing 機能が要るときは、`typing_extensions` を依存に足して使う

### Code Quality
- ruff (`ruff.toml`): 1 行 79 文字。使う規則は `select` に明示する
  (書かないと既定の規則だけになり、設定した項目も効かない)
- docstring は numpy 形式。ruff の `D` は選んでいないので、機械では検査しない
- lint (ruff, mypy) は CI で回さず、IDE と手元のコマンドで確認する。
  個人開発なので CI はテストとビルドに絞って軽く保つ
- エラーは握りつぶさず、直し方の分かるメッセージを付けて送出する

### Testing
- pytest。`tests/test_<module>.py` にモジュール単位で置く
- optional な依存に頼るテストは `pytest.importorskip` で飛ばし、
  「無い場合」は `monkeypatch.setitem(sys.modules, "<pkg>", None)` で再現する
- pytest 9 は伝播しない logger すべてに自前のハンドラを付けるので、
  ハンドラを比べるテストは pytest のものを除いて比べる

## Development Environment

### Required Tools
- Dev Container (VS Code) か、conda + `pip install -e ".[dev,test,optional,camera]"`

### Common Commands
```bash
# Test: pytest
# Lint / Format: ruff check . && ruff format .
# Type check: mypy src
# Docs: sphinx-apidoc -f -o ./docs_src ./src/<package> --module-first && sphinx-build -b html ./docs_src ./docs
# Build: python -m build
```

## Key Technical Decisions

- **conda は開発環境、pip はライブラリ**: 開発の道具は conda で揃え、
  ライブラリの依存宣言 (pyproject.toml) には持ち込まない
- **CI は paths で絞る**: 必須チェックにする workflow は `dorny/paths-filter`
  で job 単位に飛ばす (workflow ごと飛ぶと Pending のまま残るため)
- **リリース**: タグの push で build し、署名して GitHub Releases に上げる。
  PyPI には出さない (`HOW_TO_RELEASE.md`)

---
_updated_at: 2026-11-22_
