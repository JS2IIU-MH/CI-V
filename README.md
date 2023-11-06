# CI-V
CI-V communication utilities

[![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/pylint-dev/pylint)
![example workflow](https://github.com/JS2IIU-MH/CI-V/actions/workflows/pylint.yml/badge.svg)

## utilities
- test_civ.py: USBで接続したIC-7300からリグに表示している周波数の情報を取得するサンプルです。取得した周波数はターミナル上に表示されます。すでにFT8を運用している方はpyserialをインストールするだけで動くと思います。

## Reference
### CI-V
- I-COM IC-7300 補足説明書
    - [I-COMのホームページ](https://www.icom.co.jp/support/personal/)から検索してください。
- [My Project／第11回　【１度やってみたかった！】 CI-Vでハンディー機をリモート制御 ｜2017年8月号 - 月刊FBニュース　アマチュア無線の情報を満載](https://www.fbnews.jp/201708/myproject/)

### serial communication
- [Welcome to pySerial’s documentation — pySerial 3.4 documentation](https://pyserial.readthedocs.io/en/latest/index.html)
