# Obsidian S3 Backup

ObsidianのVaultデータをAWS S3に完全バックアップするPythonアプリケーションです。

## 概要

- **目的**: ObsidianのVaultを定期的にS3にバックアップ
- **形式**: ZIP圧縮アーカイブ
- **保存先**: AWS S3 (DEEP_ARCHIVE)
- **暗号化**: SSE-S3サーバーサイド暗号化

## システム要件

### 必要なソフトウェア
- Python 3.11以上
- Docker & Docker Compose（推奨）
- AWS CLI（オプション）

### AWS要件
- AWS アカウント
- S3への読み書き権限
- 必要に応じてS3バケット作成権限

## セットアップ

### 1. プロジェクトの準備

```bash
git clone <repository-url>
cd obsidian-s3-backup
```

### 2. 環境変数の設定

`.env.example`をコピーして`.env`ファイルを作成：

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```bash
# Obsidian Vault設定
OBSIDIAN_VAULT_PATH=/vault
HOST_VAULT_PATH=/path/to/your/obsidian/vault

# AWS設定
AWS_S3_BUCKET_NAME=your-obsidian-backup
AWS_REGION=ap-northeast-1

# AWS認証情報（オプション - AWS CLIプロファイルを使用する場合は不要）
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### 3. AWS認証情報の準備

以下のいずれかの方法でAWS認証を設定：

#### 方法A: 環境変数（推奨）
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

#### 方法B: AWS CLIプロファイル
```bash
aws configure
# または
aws configure --profile backup
```

#### 方法C: IAMロール（EC2等で実行する場合）
EC2インスタンスにS3アクセス権限のあるIAMロールを付与

## 実行方法

### Docker Compose使用（推奨）

#### 1. 設定確認
```bash
# .envファイルの内容を確認
cat .env
```

#### 2. ビルドと実行
```bash
# イメージをビルド
docker-compose build

# バックアップを実行
docker-compose run --rm obsidian-backup python src/main.py
```

#### 3. ワンライナーでの実行
```bash
# 環境変数を指定して実行
OBSIDIAN_VAULT_PATH=/vault \
HOST_VAULT_PATH=/path/to/your/vault \
AWS_S3_BUCKET_NAME=your-backup-bucket \
docker-compose run --rm obsidian-backup python src/main.py
```

### 直接Python実行

#### 1. 依存関係インストール
```bash
pip install -r requirements.txt
```

#### 2. 環境変数設定と実行
```bash
export OBSIDIAN_VAULT_PATH=/path/to/your/vault
export AWS_S3_BUCKET_NAME=your-backup-bucket
export AWS_REGION=ap-northeast-1

python src/main.py
```

## 設定項目

### 必須環境変数

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `OBSIDIAN_VAULT_PATH` | Vaultのパス | `/vault` |
| `AWS_S3_BUCKET_NAME` | S3バケット名 | `my-obsidian-backup` |

### オプション環境変数

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| `AWS_REGION` | `ap-northeast-1` | AWSリージョン |
| `LOG_LEVEL` | `INFO` | ログレベル（DEBUG/INFO/WARNING/ERROR） |
| `BACKUP_PREFIX` | `obsidian-backup` | バックアップファイルの接頭辞 |

## 実行例

### 成功時のログ出力例

```
[2024-01-15 12:00:00] [INFO] [obsidian_backup] === Obsidian S3 Backup Started ===
[2024-01-15 12:00:00] [INFO] [obsidian_backup] Loading configuration...
[2024-01-15 12:00:00] [INFO] [obsidian_backup] Configuration loaded - Vault: /vault, Bucket: my-backup
[2024-01-15 12:00:01] [INFO] [obsidian_backup] Validating configuration...
[2024-01-15 12:00:01] [INFO] [obsidian_backup] Configuration validation successful
[2024-01-15 12:00:01] [INFO] [obsidian_backup] Initializing AWS S3 client...
[2024-01-15 12:00:02] [INFO] [obsidian_backup] AWS credentials verified successfully. Found 3 buckets.
[2024-01-15 12:00:02] [INFO] [obsidian_backup] Starting backup process...
[2024-01-15 12:00:02] [INFO] [obsidian_backup] ObsidianBackup initialized for vault: /vault
[2024-01-15 12:00:02] [INFO] [obsidian_backup] Vault validation successful
[2024-01-15 12:00:02] [INFO] [obsidian_backup] Scanned 156 files for backup
[2024-01-15 12:00:03] [INFO] [obsidian_backup] Created archive with 156 files: /tmp/tmpxxx.zip
[2024-01-15 12:00:03] [INFO] [obsidian_backup] S3 bucket 'my-backup' already exists and is accessible
[2024-01-15 12:00:03] [INFO] [obsidian_backup] Generated metadata: 156 files, 2048576 bytes
[2024-01-15 12:00:05] [INFO] [obsidian_backup] File uploaded successfully: obsidian-backup-2024-01-15-12-00-03.zip
[2024-01-15 12:00:05] [INFO] [obsidian_backup] Backup completed successfully: obsidian-backup-2024-01-15-12-00-03.zip
[2024-01-15 12:00:05] [INFO] [obsidian_backup] Temporary archive file cleaned up
[2024-01-15 12:00:05] [INFO] [obsidian_backup] === Backup completed successfully ===
```

## 定期実行の設定

### Cron（Linux/macOS）

```bash
# crontabを編集
crontab -e

# 毎日午前2時に実行
0 2 * * * cd /path/to/obsidian-s3-backup && docker-compose run --rm obsidian-backup python src/main.py >> /var/log/obsidian-backup.log 2>&1
```

### systemd Timer（Linux）

```bash
# タイマーファイルを作成
sudo nano /etc/systemd/system/obsidian-backup.timer

# サービスファイルを作成
sudo nano /etc/systemd/system/obsidian-backup.service

# タイマーを有効化
sudo systemctl enable obsidian-backup.timer
sudo systemctl start obsidian-backup.timer
```

### GitHub Actions（推奨）

```yaml
name: Obsidian Backup
on:
  schedule:
    - cron: '0 2 * * *'  # 毎日午前2時
  workflow_dispatch:     # 手動実行も可能

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Backup
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          OBSIDIAN_VAULT_PATH: /vault
          AWS_S3_BUCKET_NAME: ${{ secrets.S3_BUCKET_NAME }}
        run: |
          docker-compose build
          docker-compose run --rm obsidian-backup python src/main.py
```

## バックアップファイル形式

### ファイル名形式
```
obsidian-backup-YYYY-MM-DD-HH-MM-SS.zip
```

例: `obsidian-backup-2024-01-15-12-30-45.zip`

### メタデータ
S3オブジェクトのメタデータに以下の情報が保存されます：
- `backup_date`: バックアップ実行日時
- `vault_path`: Vault名
- `file_count`: ファイル数
- `total_size`: 総サイズ（バイト）
- `backup_type`: バックアップタイプ（full）

## トラブルシューティング

### よくあるエラー

#### 1. AWS認証エラー
```
AWS credentials not found. Please configure AWS credentials.
```
**解決方法**: AWS認証情報を正しく設定してください。

#### 2. Vaultが見つからない
```
Vault path does not exist: /path/to/vault
```
**解決方法**: `OBSIDIAN_VAULT_PATH`または`HOST_VAULT_PATH`を正しく設定してください。

#### 3. S3バケットアクセスエラー
```
Access denied to bucket 'bucket-name'. Check your permissions.
```
**解決方法**: AWS IAMポリシーでS3への適切な権限を付与してください。

### デバッグモード

詳細なログを出力するには：
```bash
export LOG_LEVEL=DEBUG
python src/main.py
```

## 開発・テスト

### テストの実行

```bash
# 全テストを実行
python -m unittest discover -v

# 特定のテストモジュールを実行
python -m unittest tests.test_main -v
```

### コードスタイル

```bash
# コードの整形
black src/ tests/

# リントチェック
flake8 src/ tests/
```

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## サポート

問題が発生した場合は、以下を確認してください：
1. 環境変数の設定
2. AWS認証情報
3. Vaultパスの存在
4. ネットワーク接続
5. AWS権限設定

詳細なエラーログを確認し、必要に応じてGitHubのIssuesで報告してください。