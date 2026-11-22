# リリース手順

## コミット

```bash
git commit -m "Release v0.0.1"  # バージョンは適宜変更
```

## タグ

```bash
git tag v0.0.1
```

タグは頭に'v'をつける以外は、原則 [Semantic Versioning](https://semver.org/lang/ja/) に従う。

e.g.) v1.0.0 v3.2.1-alpha.0 v4.1.2-beta.1 v0.2.1-rc.0


## リリース

タグを push すると `.github/workflows/release.yml` が wheel と sdist を作り、
Sigstore で署名して GitHub Releases に上げる。PyPI / conda-forge には公開しない。

利用者は git から入れる:

```bash
pip install "qrlocal[camera] @ git+https://github.com/yu9824/qrlocal.git@v0.0.1"
```
