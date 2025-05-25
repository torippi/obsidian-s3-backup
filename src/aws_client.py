"""
AWS S3 Client Module
AWS S3との連携処理を担当するモジュール
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from typing import Optional, Dict
from dotenv import load_dotenv

class S3BackupClient:
    """
    S3バックアップクライアント
    AWS S3へのファイルアップロードとバケット管理を担当
    """
    
    def __init__(self, bucket_name: str, region: str, logger: logging.Logger):
        """
        S3BackupClientの初期化
        
        Args:
            bucket_name (str): S3バケット名
            region (str): AWSリージョン
            logger (logging.Logger): ロガーインスタンス
            
        Raises:
            ValueError: バケット名またはリージョンが空の場合
        """
        # 入力値の検証
        if not bucket_name or not isinstance(bucket_name, str):
            raise ValueError("Bucket name must be a non-empty string")
        if not region or not isinstance(region, str):
            raise ValueError("Region must be a non-empty string")
        if not logger:
            raise ValueError("Logger is required")
        
        self.bucket_name = bucket_name.strip()
        self.region = region.strip()
        self.logger = logger
        self.s3_client = None
        self.backup_prefix = "obsidian-backup"
        
        self.logger.info(f"S3BackupClient initialized for bucket '{self.bucket_name}' in region '{self.region}'")
    
    def initialize_client(self) -> bool:
        """
        S3クライアントの初期化
        AWS認証情報を使用してboto3 S3クライアントを作成
        
        Returns:
            bool: 初期化成功時はTrue、失敗時はFalse
        """
        try:
            # AWS認証情報の取得
            credentials = get_aws_credentials()
            
            if credentials:
                # 認証情報を使用してS3クライアントを作成
                self.s3_client = boto3.client(
                    's3',
                    region_name=self.region,
                    aws_access_key_id=credentials['aws_access_key_id'],
                    aws_secret_access_key=credentials['aws_secret_access_key']
                )
                self.logger.info("S3 client initialized with explicit credentials")
            else:
                # 認証情報が取得できない場合はデフォルト設定で試行
                self.s3_client = boto3.client('s3', region_name=self.region)
                self.logger.info("S3 client initialized with default credentials")
            
            return True
            
        except NoCredentialsError:
            self.logger.error("AWS credentials not found. Please configure AWS credentials.")
            self.s3_client = None
            return False
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            self.logger.error(f"AWS Client Error during initialization: {error_code} - {error_msg}")
            self.s3_client = None
            return False
            
        except BotoCoreError as e:
            self.logger.error(f"BotoCore Error during S3 client initialization: {str(e)}")
            self.s3_client = None
            return False
            
        except Exception as e:
            self.logger.error(f"Unexpected error during S3 client initialization: {str(e)}")
            self.s3_client = None
            return False
    
    def verify_credentials(self) -> bool:
        """
        AWS認証情報の検証
        S3サービスへの接続テストを実行
        
        Returns:
            bool: 認証成功時はTrue、失敗時はFalse
        """
        if not self.s3_client:
            self.logger.error("S3 client is not initialized. Call initialize_client() first.")
            return False
        
        try:
            # list_bucketsを実行して認証情報を検証
            response = self.s3_client.list_buckets()
            
            # レスポンスの基本チェック
            if 'Buckets' in response:
                bucket_count = len(response['Buckets'])
                self.logger.info(f"AWS credentials verified successfully. Found {bucket_count} buckets.")
                return True
            else:
                self.logger.warning("Unexpected response format from list_buckets")
                return False
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            if error_code == 'AccessDenied':
                self.logger.error("Access denied. Please check your AWS permissions.")
            elif error_code == 'InvalidAccessKeyId':
                self.logger.error("Invalid access key ID. Please check your AWS credentials.")
            elif error_code == 'SignatureDoesNotMatch':
                self.logger.error("Invalid secret access key. Please check your AWS credentials.")
            else:
                self.logger.error(f"AWS error during credential verification: {error_code} - {error_msg}")
            
            return False
            
        except BotoCoreError as e:
            self.logger.error(f"BotoCore error during credential verification: {str(e)}")
            return False
            
        except Exception as e:
            self.logger.error(f"Unexpected error during credential verification: {str(e)}")
            return False
        
    def ensure_bucket_exists(self) -> bool:
        """
        S3バケットの存在確認・作成
        バケットが存在しない場合は暗号化設定付きで作成
        
        Returns:
            bool: バケットが利用可能な場合はTrue、失敗時はFalse
        """
        if not self.s3_client:
            self.logger.error("S3 client is not initialized. Call initialize_client() first.")
            return False
        
        try:
            # バケットの存在確認
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            self.logger.info(f"S3 bucket '{self.bucket_name}' already exists and is accessible")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'NoSuchBucket' or error_code == '404':
                # バケットが存在しない場合は作成
                self.logger.info(f"S3 bucket '{self.bucket_name}' does not exist. Creating...")
                return self._create_bucket_with_encryption()
                
            elif error_code == 'AccessDenied' or error_code == 'Forbidden':
                self.logger.error(f"Access denied to bucket '{self.bucket_name}'. Check your permissions.")
                return False
                
            else:
                error_msg = e.response['Error']['Message']
                self.logger.error(f"Error checking bucket '{self.bucket_name}': {error_code} - {error_msg}")
                return False
                
        except BotoCoreError as e:
            self.logger.error(f"BotoCore error during bucket check: {str(e)}")
            return False
            
        except Exception as e:
            self.logger.error(f"Unexpected error during bucket check: {str(e)}")
            return False
    
    def _create_bucket_with_encryption(self) -> bool:
        """
        暗号化設定付きでS3バケットを作成（内部メソッド）
        
        Returns:
            bool: 作成成功時はTrue、失敗時はFalse
        """
        try:
            # バケット作成の設定
            create_bucket_kwargs = {'Bucket': self.bucket_name}
            
            # us-east-1以外の場合はLocationConstraintが必要
            if self.region != 'us-east-1':
                create_bucket_kwargs['CreateBucketConfiguration'] = {
                    'LocationConstraint': self.region
                }
            
            # バケットを作成
            self.s3_client.create_bucket(**create_bucket_kwargs)
            self.logger.info(f"S3 bucket '{self.bucket_name}' created successfully in region '{self.region}'")
            
            # サーバーサイド暗号化（SSE-S3）を設定
            encryption_config = {
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
            
            self.s3_client.put_bucket_encryption(
                Bucket=self.bucket_name,
                ServerSideEncryptionConfiguration=encryption_config
            )
            
            self.logger.info(f"Encryption enabled for bucket '{self.bucket_name}' with SSE-S3")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            if error_code == 'BucketAlreadyOwnedByYou':
                self.logger.info(f"Bucket '{self.bucket_name}' already exists and is owned by you")
                return True
            elif error_code == 'BucketAlreadyExists':
                self.logger.error(f"Bucket '{self.bucket_name}' already exists and is owned by someone else")
                return False
            else:
                self.logger.error(f"Failed to create bucket '{self.bucket_name}': {error_code} - {error_msg}")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error creating bucket '{self.bucket_name}': {str(e)}")
            return False

    def upload_file(self, local_path: str, s3_key: str, metadata: dict = None) -> bool:
        """
        ファイルをS3にアップロード
        
        Args:
            local_path (str): ローカルファイルパス
            s3_key (str): S3オブジェクトキー
            metadata (dict): メタデータ（オプション）
        
        Returns:
            bool: アップロード成功時はTrue、失敗時はFalse
        """
        if not self.s3_client:
            self.logger.error("S3 client is not initialized. Call initialize_client() first.")
            return False
        
        if not os.path.exists(local_path):
            self.logger.error(f"File not found: {local_path}")
            return False
        
        try:
            # アップロード設定
            extra_args = {
                'StorageClass': 'DEEP_ARCHIVE',
                'ServerSideEncryption': 'AES256'
            }
            
            # メタデータが指定されている場合は追加
            if metadata:
                extra_args['Metadata'] = metadata
            
            # ファイルアップロード
            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            self.logger.info(f"File uploaded successfully: {s3_key}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            self.logger.error(f"Failed to upload file: {error_code} - {error_msg}")
            return False
            
        except Exception as e:
            self.logger.error(f"Unexpected error during file upload: {str(e)}")
            return False
    
    def generate_backup_key(self, timestamp: str) -> str:
        """
        バックアップキーの生成
        
        Args:
            timestamp (str): タイムスタンプ文字列
        
        Returns:
            str: S3オブジェクトキー
        
        Raises:
            ValueError: タイムスタンプが空またはNoneの場合
        """
        if not timestamp or not isinstance(timestamp, str):
            raise ValueError("Timestamp must be a non-empty string")
        
        return f"{self.backup_prefix}-{timestamp}.zip"

def get_aws_credentials() -> Optional[Dict[str, str]]:
    """
    AWS認証情報を取得する
    .envファイル → 環境変数 → AWSプロファイル → IAMロールの順で確認
    
    Returns:
        Optional[Dict[str, str]]: 認証情報の辞書、取得できない場合はNone
            - aws_access_key_id: アクセスキーID
            - aws_secret_access_key: シークレットアクセスキー
    """
    logger = logging.getLogger(__name__)
    
    # 1. .envファイルから認証情報を読み込み
    try:
        # .envファイルを読み込む（存在しない場合は無視）
        load_dotenv()
        logger.info("Loaded environment variables from .env file")
    except Exception as e:
        logger.warning(f"Failed to load .env file: {e}")
    
    # 2. 環境変数から認証情報を取得（.envで設定された値も含む）
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    if access_key and secret_key:
        logger.info("AWS credentials found in environment variables (.env or system)")
        return {
            'aws_access_key_id': access_key,
            'aws_secret_access_key': secret_key
        }
    
    # 3. AWSプロファイルから認証情報を取得
    try:
        import boto3
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials and credentials.access_key and credentials.secret_key:
            logger.info("AWS credentials found in AWS profile")
            return {
                'aws_access_key_id': credentials.access_key,
                'aws_secret_access_key': credentials.secret_key
            }
    except Exception as e:
        logger.warning(f"Failed to get AWS credentials from profile: {e}")
    
    # 4. 認証情報が取得できない場合
    logger.error("AWS credentials not found. Please set in .env file, environment variables, or configure AWS CLI.")
    return None

def create_bucket_with_encryption(bucket_name: str, region: str) -> bool:
    """
    S3バケットを暗号化設定付きで作成する
    
    Args:
        bucket_name (str): 作成するバケット名
        region (str): AWSリージョン
        
    Returns:
        bool: 作成成功時はTrue、失敗時はFalse
    """
    logger = logging.getLogger(__name__)
    
    try:
        # S3クライアントを作成
        s3_client = boto3.client('s3', region_name=region)
        
        # バケット作成の設定
        create_bucket_config = {}
        
        # us-east-1以外の場合はLocationConstraintが必要
        if region != 'us-east-1':
            create_bucket_config['CreateBucketConfiguration'] = {
                'LocationConstraint': region
            }
        
        # バケットを作成
        if create_bucket_config:
            s3_client.create_bucket(
                Bucket=bucket_name,
                **create_bucket_config
            )
        else:
            s3_client.create_bucket(Bucket=bucket_name)
        
        logger.info(f"S3 bucket '{bucket_name}' created successfully in region '{region}'")
        
        # サーバーサイド暗号化（SSE-S3）を設定
        encryption_config = {
            'Rules': [
                {
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'AES256'
                    },
                    'BucketKeyEnabled': True
                }
            ]
        }
        
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration=encryption_config
        )
        
        logger.info(f"Encryption enabled for bucket '{bucket_name}' with SSE-S3")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        if error_code == 'BucketAlreadyOwnedByYou':
            logger.info(f"Bucket '{bucket_name}' already exists and is owned by you")
            return True
        elif error_code == 'BucketAlreadyExists':
            logger.error(f"Bucket '{bucket_name}' already exists and is owned by someone else")
            return False
        else:
            logger.error(f"Failed to create bucket '{bucket_name}': {error_code} - {error_msg}")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error creating bucket '{bucket_name}': {str(e)}")
        return False


def calculate_upload_progress(uploaded: int, total: int) -> float:
    """
    アップロード進捗の計算
    
    Args:
        uploaded (int): アップロード済みバイト数
        total (int): 総バイト数
        
    Returns:
        float: 進捗率（0.0〜100.0）
        
    Raises:
        ValueError: 負の値が渡された場合
    """
    # 入力値の検証
    if uploaded < 0:
        raise ValueError("Uploaded bytes cannot be negative")
    if total < 0:
        raise ValueError("Total bytes cannot be negative")
    
    # 総サイズが0の場合は0%を返す
    if total == 0:
        return 0.0
    
    # 進捗率を計算（100%を上限とする）
    progress = (uploaded / total) * 100.0
    return min(progress, 100.0)