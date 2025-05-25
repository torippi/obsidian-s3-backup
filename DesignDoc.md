# Obsidian S3 Backup - Design Document

## 1. 概要

ObsidianのVaultデータをAWS S3に完全バックアップするPythonアプリケーションの機能設計書です。

## 2. アーキテクチャ概要

```
┌─────────────────┐
│    main.py      │ ← エントリーポイント
│  (Controller)   │
└─────────────────┘
         │
         ├─────────────────┐
         │                 │
┌─────────────────┐ ┌─────────────────┐
│   backup.py     │ │  aws_client.py  │
│ (Business Logic)│ │ (AWS Interface) │
└─────────────────┘ └─────────────────┘
         │                 │
         │                 │
┌─────────────────┐ ┌─────────────────┐
│ Obsidian Vault  │ │    AWS S3       │
│   (File System) │ │   (Storage)     │
└─────────────────┘ └─────────────────┘
```

## 3. モジュール設計

### 3.1 main.py (Controller Layer)

**責務**: アプリケーションの実行制御とコーディネーション

#### 3.1.1 主要機能

- アプリケーションの初期化と設定読み込み
- ログ設定の初期化
- 各モジュール間の連携制御
- エラーハンドリングと終了処理
- 実行結果の統括管理

#### 3.1.2 関数設計

```python
def main() -> int:
    """
    メインエントリーポイント
    Returns:
        int: 終了ステータス (0: 成功, 1: 失敗)
    """

def setup_logging() -> logging.Logger:
    """
    ログ設定の初期化
    Returns:
        logging.Logger: 設定済みロガー
    """

def load_configuration() -> dict:
    """
    環境変数から設定を読み込み
    Returns:
        dict: 設定情報
    """

def validate_configuration(config: dict) -> bool:
    """
    設定値の妥当性検証
    Args:
        config: 設定情報
    Returns:
        bool: 検証結果
    """
```

#### 3.1.3 実行フロー

1. ログ設定の初期化
2. 環境変数・設定の読み込み
3. 設定値の妥当性検証
4. Vault存在確認
5. AWS接続確認
6. バックアップ実行
7. 結果レポート出力

---

### 3.2 backup.py (Business Logic Layer)

**責務**: バックアップロジックの実装

#### 3.2.1 主要機能

- Obsidian Vaultの検証とスキャン
- バックアップ対象ファイルの選別
- ファイル圧縮処理
- バックアップメタデータの生成
- 進捗管理とログ出力

#### 3.2.2 クラス設計

```python
class ObsidianBackup:
    """Obsidianバックアップの主要クラス"""
    
    def __init__(self, vault_path: str, aws_client, logger: logging.Logger):
        """
        初期化
        Args:
            vault_path: Vaultのパス
            aws_client: AWSクライアントインスタンス
            logger: ロガー
        """
    
    def validate_vault(self) -> bool:
        """
        Vaultの妥当性検証
        Returns:
            bool: 検証結果
        """
    
    def scan_vault_files(self) -> List[str]:
        """
        バックアップ対象ファイルのスキャン
        Returns:
            List[str]: ファイルパスリスト
        """
    
    def create_backup_archive(self, files: List[str]) -> str:
        """
        バックアップアーカイブの作成
        Args:
            files: ファイルリスト
        Returns:
            str: アーカイブファイルパス
        """
    
    def generate_backup_metadata(self) -> dict:
        """
        バックアップメタデータの生成
        Returns:
            dict: メタデータ情報
        """
    
    def execute_backup(self) -> bool:
        """
        バックアップの実行
        Returns:
            bool: 実行結果
        """
```

#### 3.2.3 補助関数

```python
def get_file_stats(file_path: str) -> dict:
    """ファイル統計情報の取得"""

def is_backup_target(file_path: str) -> bool:
    """バックアップ対象ファイルの判定"""

def calculate_total_size(files: List[str]) -> int:
    """総ファイルサイズの計算"""
```

#### 3.2.4 除外対象

- `.obsidian/` ディレクトリ（設定・プラグイン）
- `.DS_Store` ファイル（macOS）
- 一時ファイル（`.tmp`, `.temp`）
- 隠しファイル（`.`で始まるファイル、除外設定による）

---

### 3.3 aws_client.py (Infrastructure Layer)

**責務**: AWS S3との連携処理

#### 3.3.1 主要機能

- S3クライアントの初期化と認証
- S3バケットの存在確認・作成
- ファイルアップロード処理
- 暗号化設定の適用
- AWS APIエラーハンドリング

#### 3.3.2 クラス設計

```python
class S3BackupClient:
    """S3バックアップクライアント"""
    
    def __init__(self, bucket_name: str, region: str, logger: logging.Logger):
        """
        初期化
        Args:
            bucket_name: S3バケット名
            region: AWSリージョン
            logger: ロガー
        """
    
    def initialize_client(self) -> bool:
        """
        S3クライアントの初期化
        Returns:
            bool: 初期化結果
        """
    
    def verify_credentials(self) -> bool:
        """
        AWS認証情報の検証
        Returns:
            bool: 認証結果
        """
    
    def ensure_bucket_exists(self) -> bool:
        """
        S3バケットの存在確認・作成
        Returns:
            bool: 処理結果
        """
    
    def upload_file(self, local_path: str, s3_key: str, metadata: dict = None) -> bool:
        """
        ファイルのアップロード
        Args:
            local_path: ローカルファイルパス
            s3_key: S3オブジェクトキー
            metadata: メタデータ
        Returns:
            bool: アップロード結果
        """
    
    def generate_backup_key(self, timestamp: str) -> str:
        """
        バックアップキーの生成
        Args:
            timestamp: タイムスタンプ
        Returns:
            str: S3オブジェクトキー
        """
```

#### 3.3.3 補助関数

```python
def get_aws_credentials() -> dict:
    """AWS認証情報の取得"""

def create_bucket_with_encryption(bucket_name: str, region: str) -> bool:
    """暗号化設定付きバケット作成"""

def calculate_upload_progress(uploaded: int, total: int) -> float:
    """アップロード進捗の計算"""
```

#### 3.3.4 S3設定

- **暗号化**: SSE-S3（サーバーサイド暗号化）
- **ストレージクラス**: DEEP_ARCHIVE（長期保存・低コスト）
- **オブジェクトキー形式**: `obsidian-backup-YYYY-MM-DD-HH-MM-SS.zip`

---

## 4. データフロー

```
1. [main.py] 設定読み込み・初期化
           ↓
2. [backup.py] Vault検証・ファイルスキャン
           ↓
3. [backup.py] アーカイブ作成
           ↓
4. [aws_client.py] S3接続・バケット確認
           ↓
5. [aws_client.py] ファイルアップロード
           ↓
6. [main.py] 結果レポート・ログ出力
```

## 5. エラーハンドリング戦略

### 5.1 レベル別エラー処理

|レベル|処理方針|例|
|---|---|---|
|**CRITICAL**|即座に終了|AWS認証失敗、Vaultが存在しない|
|**ERROR**|処理継続を試行|個別ファイルの読み込み失敗|
|**WARNING**|ログ記録のみ|スキップされたファイル|
|**INFO**|進捗情報|処理開始・完了|

### 5.2 リトライ機能

- **対象**: ネットワークエラー、一時的なAWS APIエラー
- **回数**: 最大3回
- **間隔**: 指数バックオフ（1秒、2秒、4秒）

## 6. ログ仕様

### 6.1 ログレベル

- **DEBUG**: 詳細な実行情報（開発時のみ）
- **INFO**: 一般的な実行情報
- **WARNING**: 警告レベルの問題
- **ERROR**: エラーレベルの問題
- **CRITICAL**: 致命的な問題

### 6.2 ログ出力先

- **コンソール**: カラー付きログ（開発時）
- **ファイル**: `/app/logs/backup_YYYY-MM-DD.log`

### 6.3 ログフォーマット

```
[YYYY-MM-DD HH:MM:SS] [LEVEL] [module.function] message
```

## 7. 設定・環境変数

|変数名|必須|デフォルト|説明|
|---|---|---|---|
|`OBSIDIAN_VAULT_PATH`|Yes|-|Vaultパス|
|`AWS_S3_BUCKET_NAME`|Yes|-|S3バケット名|
|`AWS_REGION`|No|ap-northeast-1|AWSリージョン|
|`LOG_LEVEL`|No|INFO|ログレベル|
|`BACKUP_PREFIX`|No|obsidian-backup|バックアップファイル接頭辞|

## 8. パフォーマンス考慮事項

- **圧縮**: ZIP形式、圧縮レベル6（バランス重視）
- **メモリ使用量**: ストリーミング処理で大容量対応
- **並行処理**: 現バージョンでは非対応（将来拡張予定）

## 9. テスト戦略

### 9.1 単体テスト

- 各クラス・関数の個別テスト
- モックを使用したAWS API呼び出しテスト

### 9.2 統合テスト

- 実際のVaultを使用したE2Eテスト
- AWS S3との実際の連携テスト

### 9.3 エラーケーステスト

- ネットワーク障害シミュレーション
- 権限不足エラーのテスト

## 10. 今後の拡張予定

- 差分バックアップ機能
- 復元機能
- 複数Vault対応
- バックアップスケジューリング
- Webダッシュボード