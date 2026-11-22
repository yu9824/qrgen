# Product Overview

`qrlocal` は、QR コードの生成と読み取りをローカルだけで行う Python
ライブラリ兼 CLI。ネットワークに一切つながずに動き、オフラインでも使える。

## Core Capabilities

- **生成**: 任意のテキストを QR コードにする。PNG / SVG に保存するか、
  端末にそのまま表示する
- **読み取り**: 画像ファイル、または PC のカメラに映した QR コードを
  テキストに戻す (カメラは optional extra `camera`)
- **CLI**: `qrlocal encode` / `qrlocal decode` / `qrlocal scan`

## Target Use Cases

- Wi-Fi のパスワードや URL など、外部の Web サービスに渡したくない
  文字列を QR にしてスマホへ渡す
- 手元の QR コードの中身を、URL を開いたりせずに確かめる

## Security Principles

- **通信しない**: 生成も読み取りもローカルで完結させ、ネットワークを使う
  依存を入れない。テストでソケットを塞いで確かめる
- **読んだ内容を信用しない**: 読み取ったテキストを開く・実行することはしない。
  CLI で表示するときは制御文字をエスケープし、端末への注入を防ぐ
- **痕跡を残さない**: カメラ映像はメモリ上で扱い、ディスクに書かない。
  秘密の文字列は stdin から渡せるようにして、shell の履歴に残さない
- **既存ファイルを壊さない**: 出力先が既にあれば、明示しない限り上書きしない

## 配布

PyPI には出さない。GitHub Releases と `pip install git+...` で配る
(`HOW_TO_RELEASE.md`)。

---
_updated_at: 2026-11-22_
