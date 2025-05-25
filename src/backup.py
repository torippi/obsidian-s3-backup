"""
Obsidian Backup Module
ObsidianのVaultデータをバックアップするためのモジュール
"""

import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

class ObsidianBackup:
    """
    Obsidianバックアップの主要クラス
    Vaultのスキャン、アーカイブ作成、S3アップロードを管理
    """
    
    def __init__(self, vault_path: str, aws_client, logger: logging.Logger):
        """
        ObsidianBackupの初期化
        
        Args:
            vault_path (str): ObsidianのVaultパス
            aws_client: AWSクライアントインスタンス
            logger (logging.Logger): ロガー
            
        Raises:
            ValueError: Vaultパスが無効な場合
        """
        if not vault_path or not isinstance(vault_path, str):
            raise ValueError("Vault path must be a non-empty string")
        
        if not os.path.exists(vault_path):
            raise ValueError(f"Vault path does not exist: {vault_path}")
        
        if not os.path.isdir(vault_path):
            raise ValueError(f"Vault path is not a directory: {vault_path}")
        
        self.vault_path = vault_path.strip()
        self.aws_client = aws_client
        self.logger = logger
        
        self.logger.info(f"ObsidianBackup initialized for vault: {self.vault_path}")
    
    def validate_vault(self) -> bool:
        """
        Vaultの妥当性検証
        
        Returns:
            bool: 有効なVaultの場合True
        """
        try:
            # ディレクトリ内のファイルをチェック
            has_md_files = False
            has_any_files = False
            
            for root, dirs, files in os.walk(self.vault_path):
                for file in files:
                    if is_backup_target(os.path.join(root, file)):
                        has_any_files = True
                        if file.endswith('.md'):
                            has_md_files = True
                            break
                
                if has_md_files:
                    break
            
            if not has_any_files:
                self.logger.warning("Vault appears to be empty or contains no valid files")
                return False
            
            if not has_md_files:
                self.logger.warning("No markdown files found in vault")
                return False
            
            self.logger.info("Vault validation successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during vault validation: {str(e)}")
            return False
    
    def scan_vault_files(self) -> List[str]:
        """
        バックアップ対象ファイルのスキャン
        
        Returns:
            List[str]: ファイルパスのリスト
        """
        files = []
        
        try:
            for root, dirs, filenames in os.walk(self.vault_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    
                    if is_backup_target(file_path):
                        files.append(file_path)
            
            self.logger.info(f"Scanned {len(files)} files for backup")
            return files
            
        except Exception as e:
            self.logger.error(f"Error during file scanning: {str(e)}")
            return []
    
    def create_backup_archive(self, files: List[str]) -> Optional[str]:
        """
        バックアップアーカイブの作成
        
        Args:
            files (List[str]): ファイルパスのリスト
            
        Returns:
            Optional[str]: アーカイブファイルパス、失敗時はNone
        """
        if not files:
            self.logger.error("No files to archive")
            return None
        
        try:
            # 一時ファイル作成
            temp_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
            archive_path = temp_file.name
            temp_file.close()
            
            # ZIPアーカイブ作成
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                archived_count = 0
                
                for file_path in files:
                    if not os.path.exists(file_path):
                        self.logger.warning(f"File not found, skipping: {file_path}")
                        continue
                    
                    try:
                        # Vault相対パスを計算
                        relative_path = os.path.relpath(file_path, self.vault_path)
                        zip_file.write(file_path, relative_path)
                        archived_count += 1
                        
                    except Exception as e:
                        self.logger.warning(f"Failed to add file to archive: {file_path} - {str(e)}")
                        continue
                
                if archived_count == 0:
                    self.logger.error("No files were successfully archived")
                    os.unlink(archive_path)
                    return None
                
                self.logger.info(f"Created archive with {archived_count} files: {archive_path}")
                return archive_path
                
        except Exception as e:
            self.logger.error(f"Error creating backup archive: {str(e)}")
            return None
    
    def generate_backup_metadata(self) -> Dict:
        """
        バックアップメタデータの生成
        
        Returns:
            Dict: メタデータ情報
        """
        files = self.scan_vault_files()
        total_size = calculate_total_size(files)
        
        metadata = {
            'backup_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'vault_path': os.path.basename(self.vault_path),
            'file_count': str(len(files)),
            'total_size': str(total_size),
            'backup_type': 'full'
        }
        
        self.logger.info(f"Generated metadata: {len(files)} files, {total_size} bytes")
        return metadata
    
    def execute_backup(self) -> bool:
        """
        バックアップの実行
        
        Returns:
            bool: バックアップ成功時はTrue
        """
        try:
            self.logger.info("Starting backup execution")
            
            # 1. Vault検証
            if not self.validate_vault():
                self.logger.error("Vault validation failed")
                return False
            
            # 2. ファイルスキャン
            files = self.scan_vault_files()
            if not files:
                self.logger.error("No files found to backup")
                return False
            
            # 3. アーカイブ作成
            archive_path = self.create_backup_archive(files)
            if not archive_path:
                self.logger.error("Failed to create backup archive")
                return False
            
            try:
                # 4. S3バケット確認
                if not self.aws_client.ensure_bucket_exists():
                    self.logger.error("Failed to ensure S3 bucket exists")
                    return False
                
                # 5. バックアップキー生成
                timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
                s3_key = self.aws_client.generate_backup_key(timestamp)
                
                # 6. メタデータ生成
                metadata = self.generate_backup_metadata()
                
                # 7. S3アップロード
                if not self.aws_client.upload_file(archive_path, s3_key, metadata):
                    self.logger.error("Failed to upload backup to S3")
                    return False
                
                self.logger.info(f"Backup completed successfully: {s3_key}")
                return True
                
            finally:
                # 一時ファイルのクリーンアップ
                if os.path.exists(archive_path):
                    os.unlink(archive_path)
                    self.logger.info("Temporary archive file cleaned up")
                
        except Exception as e:
            self.logger.error(f"Unexpected error during backup execution: {str(e)}")
            return False


def get_file_stats(file_path: str) -> Optional[Dict]:
    """
    ファイルの統計情報を取得
    
    Args:
        file_path (str): ファイルパス
    
    Returns:
        Optional[Dict]: ファイル統計情報、取得失敗時はNone
            - size: ファイルサイズ（バイト）
            - modified_time: 最終更新日時
    """
    try:
        if not os.path.exists(file_path):
            return None
        
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'modified_time': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception:
        return None


def is_backup_target(file_path: str) -> bool:
    """
    ファイルがバックアップ対象かどうかを判定
    
    Args:
        file_path (str): ファイルパス
    
    Returns:
        bool: バックアップ対象の場合True
    """
    # ファイル名とディレクトリ名を取得
    file_name = os.path.basename(file_path)
    dir_path = os.path.dirname(file_path)
    
    # 除外対象：.obsidianディレクトリ内のファイル
    if '.obsidian' in file_path:
        return False
    
    # 除外対象：システムファイル
    excluded_files = ['.DS_Store', 'Thumbs.db', '.gitignore']
    if file_name in excluded_files:
        return False
    
    # 除外対象：一時ファイル
    temp_extensions = ['.tmp', '.temp', '.bak', '.swp']
    if any(file_name.endswith(ext) for ext in temp_extensions):
        return False
    
    # 除外対象：隠しファイル（.で始まるファイル）
    if file_name.startswith('.'):
        return False
    
    # 対象：通常のファイル
    return True


def calculate_total_size(files: List[str]) -> int:
    """
    ファイルリストの総サイズを計算
    
    Args:
        files (List[str]): ファイルパスのリスト
    
    Returns:
        int: 総サイズ（バイト）
    """
    total_size = 0
    
    for file_path in files:
        try:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                total_size += os.path.getsize(file_path)
        except Exception:
            # ファイル読み取りエラーは無視して続行
            continue
    
    return total_size