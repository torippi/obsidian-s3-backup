"""
Backup Module Unit Tests
backup.pyの単体テスト - 正常系・異常系をカバー
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import logging
import tempfile
import zipfile
from datetime import datetime

# テスト中のログ出力を無効化
logging.disable(logging.CRITICAL)

# srcディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# テスト対象のモジュールをインポート（実装後に有効化）
from backup import ObsidianBackup, get_file_stats, is_backup_target, calculate_total_size

class TestObsidianBackup(unittest.TestCase):
    """ObsidianBackupクラスのテスト"""
    
    def setUp(self):
        """各テストの前処理"""
        # テスト用の一時ディレクトリ作成
        self.temp_dir = tempfile.mkdtemp()
        self.vault_path = self.temp_dir
        
        # テスト用ファイルの作成
        self.test_md_file = os.path.join(self.temp_dir, "test.md")
        with open(self.test_md_file, 'w') as f:
            f.write("# Test Note\nThis is a test markdown file.")
        
        self.test_image_file = os.path.join(self.temp_dir, "image.png")
        with open(self.test_image_file, 'wb') as f:
            f.write(b"fake image data")
        
        # .obsidianディレクトリ（除外対象）
        self.obsidian_dir = os.path.join(self.temp_dir, ".obsidian")
        os.makedirs(self.obsidian_dir)
        with open(os.path.join(self.obsidian_dir, "config.json"), 'w') as f:
            f.write('{"test": "config"}')
        
        # AWS クライアントのモック
        self.mock_aws_client = Mock()
        self.logger = Mock(spec=logging.Logger)
        
        # ObsidianBackupのインスタンス作成（実装後に有効化）
        self.backup = ObsidianBackup(self.vault_path, self.mock_aws_client, self.logger)
    
    def tearDown(self):
        """各テストの後処理"""
        # テスト用ディレクトリの削除
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ===== __init__メソッドのテスト =====
    def test_init_success(self):
        """正常系: 初期化が正常に完了する"""
        self.assertEqual(self.backup.vault_path, self.vault_path)
        self.assertEqual(self.backup.aws_client, self.mock_aws_client)
        self.assertEqual(self.backup.logger, self.logger)
        pass
    
    def test_init_with_nonexistent_vault(self):
        """異常系: 存在しないVaultパス"""
        nonexistent_path = "/nonexistent/vault/path"
        with self.assertRaises(ValueError):
            ObsidianBackup(nonexistent_path, self.mock_aws_client, self.logger)
        pass
    
    def test_init_with_none_vault_path(self):
        """異常系: VaultパスがNone"""
        with self.assertRaises(ValueError):
            ObsidianBackup(None, self.mock_aws_client, self.logger)
        pass

    # ===== validate_vaultメソッドのテスト =====
    def test_validate_vault_success(self):
        """正常系: 有効なVaultの検証成功"""
        result = self.backup.validate_vault()
        self.assertTrue(result)
        self.logger.info.assert_called()
        pass
    
    def test_validate_vault_no_md_files(self):
        """異常系: .mdファイルが存在しない"""
        # .mdファイルを削除
        os.remove(self.test_md_file)
        
        result = self.backup.validate_vault()
        self.assertFalse(result)
        self.logger.warning.assert_called()
        pass
    
    def test_validate_vault_empty_directory(self):
        empty_dir = tempfile.mkdtemp()
        try:
            backup = ObsidianBackup(empty_dir, self.mock_aws_client, self.logger)
            result = backup.validate_vault()
            self.assertFalse(result)
        finally:
            import shutil
            shutil.rmtree(empty_dir, ignore_errors=True)

    # ===== scan_vault_filesメソッドのテスト =====
    def test_scan_vault_files_success(self):
        """正常系: Vaultファイルのスキャン成功"""
        files = self.backup.scan_vault_files()
        self.assertIsInstance(files, list)
        self.assertGreater(len(files), 0)
         
        # .mdファイルが含まれることを確認
        md_files = [f for f in files if f.endswith('.md')]
        self.assertGreater(len(md_files), 0)
         
        # .obsidianディレクトリが除外されることを確認
        obsidian_files = [f for f in files if '.obsidian' in f]
        self.assertEqual(len(obsidian_files), 0)
        pass
    
    def test_scan_vault_files_with_subdirectories(self):
        """正常系: サブディレクトリを含むスキャン"""
        # サブディレクトリとファイルを作成
        sub_dir = os.path.join(self.temp_dir, "notes", "daily")
        os.makedirs(sub_dir)
        
        sub_file = os.path.join(sub_dir, "daily_note.md")
        with open(sub_file, 'w') as f:
            f.write("# Daily Note")
        
        files = self.backup.scan_vault_files()
        sub_files = [f for f in files if 'notes/daily' in f]
        self.assertGreater(len(sub_files), 0)
        pass

    # ===== create_backup_archiveメソッドのテスト =====
    def test_create_backup_archive_success(self):
        files = [self.test_md_file, self.test_image_file]
        
        archive_path = self.backup.create_backup_archive(files)
        
        self.assertIsNotNone(archive_path)  # ←追加：Noneチェック
        self.assertTrue(os.path.exists(archive_path))
        self.assertTrue(archive_path.endswith('.zip'))
        
        # アーカイブの内容を確認
        with zipfile.ZipFile(archive_path, 'r') as zip_file:
            zip_contents = zip_file.namelist()
            self.assertIn('test.md', zip_contents)
            self.assertIn('image.png', zip_contents)
        
        # クリーンアップ
        os.unlink(archive_path)
        
    def test_create_backup_archive_empty_file_list(self):
        """異常系: 空のファイルリスト"""
        files = []
        
        archive_path = self.backup.create_backup_archive(files)
        self.assertIsNone(archive_path)
        self.logger.error.assert_called()
        pass
    
    def test_create_backup_archive_nonexistent_files(self):
        """異常系: 存在しないファイルを含む"""
        files = [self.test_md_file, "/nonexistent/file.md"]
        
        archive_path = self.backup.create_backup_archive(files)
        self.assertIsNotNone(archive_path)  # 存在するファイルのみでアーカイブ作成
        self.logger.warning.assert_called()  # 警告ログが出力される
        pass

    # ===== generate_backup_metadataメソッドのテスト =====
    def test_generate_backup_metadata_success(self):
        """正常系: バックアップメタデータの生成成功"""
        metadata = self.backup.generate_backup_metadata()
        
        self.assertIsInstance(metadata, dict)
        self.assertIn('backup_date', metadata)
        self.assertIn('vault_path', metadata)
        self.assertIn('file_count', metadata)
        self.assertIn('total_size', metadata)
        pass
    
    def test_generate_backup_metadata_custom_info(self):
        """正常系: カスタム情報を含むメタデータ"""
        metadata = self.backup.generate_backup_metadata()
        
        # タイムスタンプの形式を確認
        backup_date = metadata.get('backup_date')
        self.assertIsNotNone(backup_date)
        datetime.strptime(backup_date, '%Y-%m-%d %H:%M:%S')  # 形式チェック
        pass

    # ===== execute_backupメソッドのテスト =====
    def test_execute_backup_success(self):
        """正常系: バックアップ実行成功"""
        # AWS クライアントのモック設定
        self.mock_aws_client.ensure_bucket_exists.return_value = True
        self.mock_aws_client.upload_file.return_value = True
        self.mock_aws_client.generate_backup_key.return_value = "test-backup-key.zip"
        
        result = self.backup.execute_backup()
        
        self.assertTrue(result)
        self.mock_aws_client.ensure_bucket_exists.assert_called_once()
        self.mock_aws_client.upload_file.assert_called_once()
        self.logger.info.assert_called()
        pass
    
    def test_execute_backup_bucket_creation_failure(self):
        """異常系: バケット作成失敗"""
        self.mock_aws_client.ensure_bucket_exists.return_value = False
        
        result = self.backup.execute_backup()
         
        self.assertFalse(result)
        self.mock_aws_client.ensure_bucket_exists.assert_called_once()
        self.mock_aws_client.upload_file.assert_not_called()
        self.logger.error.assert_called()
        pass
    
    def test_execute_backup_upload_failure(self):
        """異常系: ファイルアップロード失敗"""
        self.mock_aws_client.ensure_bucket_exists.return_value = True
        self.mock_aws_client.upload_file.return_value = False
        self.mock_aws_client.generate_backup_key.return_value = "test-backup-key.zip"
        
        result = self.backup.execute_backup()
         
        self.assertFalse(result)
        self.mock_aws_client.upload_file.assert_called_once()
        self.logger.error.assert_called()
        pass


class TestBackupHelperFunctions(unittest.TestCase):
    """バックアップ補助関数のテスト"""
    
    def setUp(self):
        """各テストの前処理"""
        # テスト用ファイル作成
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.md')
        self.temp_file.write(b"Test content")
        self.temp_file.close()
        self.test_file_path = self.temp_file.name

    def tearDown(self):
        """各テストの後処理"""
        if os.path.exists(self.test_file_path):
            os.unlink(self.test_file_path)

    # ===== get_file_statsのテスト =====
    def test_get_file_stats_success(self):
        """正常系: ファイル統計情報の取得成功"""
        stats = get_file_stats(self.test_file_path)

        self.assertIsInstance(stats, dict)
        self.assertIn('size', stats)
        self.assertIn('modified_time', stats)
        self.assertGreater(stats['size'], 0)
        pass
    
    def test_get_file_stats_nonexistent_file(self):
        """異常系: 存在しないファイル"""
        stats = get_file_stats('/nonexistent/file.txt')
        self.assertIsNone(stats)
        pass

    # ===== is_backup_targetのテスト =====
    def test_is_backup_target_md_file(self):
        """正常系: .mdファイルはバックアップ対象"""
        result = is_backup_target('/path/to/note.md')
        self.assertTrue(result)
        pass
    
    def test_is_backup_target_image_file(self):
        """正常系: 画像ファイルはバックアップ対象"""
        result = is_backup_target('/path/to/image.png')
        self.assertTrue(result)
        pass
    
    def test_is_backup_target_obsidian_config(self):
        """正常系: .obsidianディレクトリ内のファイルは除外"""
        result = is_backup_target('/vault/.obsidian/config.json')
        self.assertFalse(result)
        pass
    
    def test_is_backup_target_ds_store(self):
        """正常系: .DS_Storeファイルは除外"""
        result = is_backup_target('/vault/.DS_Store')
        self.assertFalse(result)
        pass
    
    def test_is_backup_target_temp_file(self):
        """正常系: 一時ファイルは除外"""
        result = is_backup_target('/vault/temp.tmp')
        self.assertFalse(result)
        pass

    # ===== calculate_total_sizeのテスト =====
    def test_calculate_total_size_success(self):
        """正常系: 総ファイルサイズの計算成功"""
        files = [self.test_file_path]
        
        total_size = calculate_total_size(files)
        self.assertIsInstance(total_size, int)
        self.assertGreater(total_size, 0)
        pass
    
    def test_calculate_total_size_empty_list(self):
        """正常系: 空のファイルリスト"""
        files = []
        
        total_size = calculate_total_size(files)
        self.assertEqual(total_size, 0)
        pass
    
    def test_calculate_total_size_nonexistent_files(self):
        """正常系: 存在しないファイルは無視"""
        files = [self.test_file_path, '/nonexistent/file.txt']
        
        total_size = calculate_total_size(files)
        self.assertGreater(total_size, 0)  # 存在するファイルのサイズのみ
        pass


# テスト実行
if __name__ == '__main__':
    unittest.main(verbosity=2)