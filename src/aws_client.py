"""
AWS S3 Client Module
AWS S3との連携処理を担当するモジュール
"""

import os
import logging
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict


def get_aws_credentials() -> Optional[Dict[str, str]]:
    """
    AWS認証情報を取得する
    環境変数 → AWSプロファイル → IAMロールの順で確認
    
    Returns:
        Optional[Dict[str, str]]: 認証情報の辞書、取得できない場合はNone
            - aws_access_key_id: アクセスキーID
            - aws_secret_access_key: シークレットアクセスキー
    """
    logger = logging.getLogger(__name__)
    
    # 1. 環境変数から認証情報を取得
    access_key = os.getenv('AWS_ACCESS_KEY_ID')
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    
    if access_key and secret_key:
        logger.info("AWS credentials found in environment variables")
        return {
            'aws_access_key_id': access_key,
            'aws_secret_access_key': secret_key
        }
    
    # 2. AWSプロファイルから認証情報を取得
    try:
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
    
    # 3. 認証情報が取得できない場合
    logger.error("AWS credentials not found. Please set environment variables or configure AWS CLI.")
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