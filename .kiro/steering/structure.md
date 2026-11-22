# Project Structure

## Organization Philosophy

配布するコード (`src/`) とそのテスト (`tests/`) だけを置く。公開 API は
パッケージ直下で再 export し、CLI はその API を呼ぶだけの薄い層にする。

## Directory Patterns

### ライブラリ本体
**Location**: `src/<package>/`
**Purpose**: 配布するコード。機能ごとに非公開モジュールかサブパッケージ
(`logging/`, `helpers/`) に分ける
**Example**: 実装は `_` 付きの非公開モジュール (`helpers/_helpers.py`) に書き、
`__init__.py` で再 export して `__all__` に並べる。Sphinx は `__all__` にある
名前だけをドキュメントにする

### テスト
**Location**: `tests/`
**Purpose**: インストールされたパッケージに対する pytest
**Example**: `tests/test_helpers.py`。重い optional 依存を使うものは別ファイル
にして、ファイル単位でスキップできるようにする

### 環境
**Location**: `.devcontainer/`
**Purpose**: 開発用コンテナ (compose + conda 環境)

### その他
- `docs_src/`: Sphinx のソース

## Naming Conventions

- **Modules**: snake_case。非公開モジュールは `_` で始める
- **Classes**: PascalCase。ただし `with` で使うコンテキストマネージャは関数風の
  snake_case (`catch_default_handler`)
- **Functions**: snake_case

## Import Organization

```python
# パッケージ内は相対 import
from ._helpers import is_installed


# optional な依存は、使う関数の中で import する
def run():
    if not is_installed("cv2"):
        raise ImportError("... requires OpenCV; `pip install ...`")
    import cv2
```

## Code Organization Principles

- **ログ**: ライブラリ内では `print` せず、`get_child_logger(__name__)` で
  得た logger を使う。ライブラリのルート logger は親に伝播しない
- **optional な依存**: モジュールの先頭で import しない。無ければ使った時点で
  インストール方法つきの `ImportError` を出す
- **副作用を小さく**: グローバル状態を書き換える処理 (logger のハンドラ、
  ライブラリのメソッド差し替え) はコンテキストマネージャにし、抜けるときに
  入る前の状態へ戻す

---
_updated_at: 2026-11-22_
