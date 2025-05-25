"""
Obsidian S3 Backup - Main Module
アプリケーションのエントリーポイント
"""

import os
import sys
import logging
from datetime import datetime

# 相対インポート用にsrcディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.backup import ObsidianBackup
from src.aws_client import S3BackupClient

def setup_logging() -> logging.Logger:
    """
    ログ設定の初期化
    
    Returns:
        logging.Logger: 設定済みロガー
    """
    # ログレベルの設定（環境変数から取得、デフォルトはINFO）
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # ログフォーマットの設定
    log_format = '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # ロガーの設定
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(),  # コンソール出力
        ]
    )
    
    # メインロガーを取得
    logger = logging.getLogger('obsidian_backup')
    logger.info(f"Logging initialized with level: {log_level}")
    
    return logger


def load_configuration() -> dict:
    """
    環境変数から設定を読み込み
    
    Returns:
        dict: 設定情報
        
    Raises:
        ValueError: 必須環境変数が不足している場合
    """
    # 必須環境変数の確認
    vault_path = os.getenv('OBSIDIAN_VAULT_PATH')
    bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
    
    if not vault_path:
        raise ValueError("OBSIDIAN_VAULT_PATH environment variable is required")
    
    if not bucket_name:
        raise ValueError("AWS_S3_BUCKET_NAME environment variable is required")
    
    # 設定情報の構築
    config = {
        'vault_path': vault_path.strip(),
        'bucket_name': bucket_name.strip(),
        'region': os.getenv('AWS_REGION', 'ap-northeast-1').strip(),
        'log_level': os.getenv('LOG_LEVEL', 'INFO').strip().upper(),
        'backup_prefix': os.getenv('BACKUP_PREFIX', 'obsidian-backup').strip()
    }
    
    return config


def validate_configuration(config: dict) -> bool:
    """
    設定値の妥当性検証
    
    Args:
        config (dict): 設定情報
        
    Returns:
        bool: 検証結果
    """
    logger = logging.getLogger('obsidian_backup')
    
    # Vaultパスの検証
    vault_path = config.get('vault_path')
    if not vault_path:
        logger.error("Vault path is empty")
        return False
    
    if not os.path.exists(vault_path):
        logger.error(f"Vault path does not exist: {vault_path}")
        return False
    
    if not os.path.isdir(vault_path):
        logger.error(f"Vault path is not a directory: {vault_path}")
        return False
    
    # S3バケット名の基本検証
    bucket_name = config.get('bucket_name')
    if not bucket_name:
        logger.error("S3 bucket name is empty")
        return False
    
    # バケット名の基本的な文字チェック
    if not bucket_name.replace('-', '').replace('.', '').isalnum():
        logger.error(f"Invalid S3 bucket name format: {bucket_name}")
        return False
    
    # AWSリージョンの検証
    region = config.get('region')
    if not region:
        logger.error("AWS region is empty")
        return False
    
    logger.info("Configuration validation successful")
    return True


def main() -> int:
    """
    メインエントリーポイント
    
    Returns:
        int: 終了ステータス (0: 成功, 1: 失敗)
    """
    logger = None
    
    try:
        # 1. ログ設定の初期化
        logger = setup_logging()
        logger.info("=== Obsidian S3 Backup Started ===")
        
        # 2. 設定の読み込み
        logger.info("Loading configuration...")
        config = load_configuration()
        logger.info(f"Configuration loaded - Vault: {config['vault_path']}, Bucket: {config['bucket_name']}")
        
        # 3. 設定値の妥当性検証
        logger.info("Validating configuration...")
        if not validate_configuration(config):
            logger.error("Configuration validation failed")
            return 1
        
        # 4. AWS S3クライアントの初期化
        logger.info("Initializing AWS S3 client...")
        s3_client = S3BackupClient(
            bucket_name=config['bucket_name'],
            region=config['region'],
            logger=logger
        )
        
        # 5. S3クライアントの接続確認
        if not s3_client.initialize_client():
            logger.error("Failed to initialize S3 client")
            return 1
        
        if not s3_client.verify_credentials():
            logger.error("Failed to verify AWS credentials")
            return 1
        
        # 6. バックアップ処理の実行
        logger.info("Starting backup process...")
        backup = ObsidianBackup(
            vault_path=config['vault_path'],
            aws_client=s3_client,
            logger=logger
        )
        
        # 7. バックアップの実行
        if backup.execute_backup():
            logger.info("=== Backup completed successfully ===")
            return 0
        else:
            logger.error("=== Backup failed ===")
            return 1
            
    except ValueError as e:
        if logger:
            logger.error(f"Configuration error: {str(e)}")
        else:
            print(f"Configuration error: {str(e)}")
        return 1
        
    except KeyboardInterrupt:
        if logger:
            logger.info("Backup interrupted by user")
        else:
            print("Backup interrupted by user")
        return 1
        
    except Exception as e:
        if logger:
            logger.error(f"Unexpected error: {str(e)}")
        else:
            print(f"Unexpected error: {str(e)}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)