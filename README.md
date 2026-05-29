# Dormitory Bot

このリポジトリは、寮のメニューや通知を管理するためのものです。
基本的な作業は Codex にお願いする前提なので、人間向けの説明は最小限にしています。

作業の入口は [AGENTS.md](/home/kazu/dormitory/AGENTS.md) を見てください。

## ざっくり何をするか

- `data/menu.json` にメニューを保存する
- Discord にメニュー通知を送る
- 掃除関連の通知を送る

## よく使うもの

- メニュー追加: `python3 -m dormitory_bot.ingest`
- メニュー通知: `python3 -m dormitory_bot.menu_notify`
- 掃除通知: `python3 -m dormitory_bot.cleaning_notify`
- 公開用のメニュー一覧: `menu/index.html`

## メモ

- メニューの保存形式と運用ルールは [docs/menu_handoff.md](/home/kazu/dormitory/docs/menu_handoff.md) にまとめています。
- 新しいチャットでメニュー作業を始めるときは、まず [AGENTS.md](/home/kazu/dormitory/AGENTS.md) を読めば大丈夫です。
