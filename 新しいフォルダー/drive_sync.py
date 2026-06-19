import os
import sys
import argparse
import boto3
from datetime import datetime, timezone

# 引数でローカルパスを指定できるようにする
parser = argparse.ArgumentParser(description="GoogleドライブをS3に同期")
parser.add_argument("folder_path", help="同期するローカルフォルダのパス")
parser.add_argument("--bucket", default="rag-document-535179725289-ap-northeast-1-an", help="S3バケット名")
parser.add_argument("--prefix", default="TEST/", help="S3内の保存先フォルダ（プレフィックス）")
args = parser.parse_args()

# 設定
bucket_name = args.bucket
s3_folder = args.prefix
local_folder = os.path.abspath(args.folder_path)

# ------------------------------------------
# 0. 実行環境の判定（手動 vs 自動）
# ------------------------------------------
USE_TQDM = False
if sys.stdout.isatty():
    try:
        from tqdm import tqdm
        USE_TQDM = True
    except ImportError:
        pass

s3 = boto3.client('s3')
print(f"[{datetime.now()}] 同期処理を開始します。対象: {local_folder}")

# ------------------------------------------
# 1. S3情報の取得（既存ロジック）
# ------------------------------------------
s3_files = {}
try:
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name, Prefix=s3_folder):
        if 'Contents' in page:
            for obj in page['Contents']:
                s3_files[obj['Key']] = {'Size': obj['Size'], 'LastModified': obj['LastModified']}
except Exception as e:
    print(f"【エラー】S3接続失敗: {e}"); exit(1)

# ------------------------------------------
# 2. ローカルスキャンとアップロード・削除リストの作成
# ------------------------------------------
tasks_to_upload, tasks_to_delete = [], []
skipped_count = 0
local_s3_keys = set()

for root, dirs, files in os.walk(local_folder):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for file in files:
        if file.startswith('.'): continue
        
        local_path = os.path.join(root, file)
        relative_path = os.path.relpath(local_path, local_folder)
        s3_key = os.path.join(s3_folder, relative_path).replace("\\", "/")
        local_s3_keys.add(s3_key)
        
        local_size = os.path.getsize(local_path)
        local_dt = datetime.fromtimestamp(os.path.getmtime(local_path), timezone.utc)
        
        if s3_key in s3_files and local_size == s3_files[s3_key]['Size'] and local_dt <= s3_files[s3_key]['LastModified']:
            skipped_count += 1
            continue
        tasks_to_upload.append((local_path, s3_key))

for s3_key in s3_files.keys():
    if not s3_key.endswith('/') and s3_key not in local_s3_keys:
        tasks_to_delete.append(s3_key)

# ------------------------------------------
# 3. 実行（アップロード・削除）
# ------------------------------------------
# (省略: 実行ロジックはmilaupload.pyと同様に USE_TQDM で条件分岐)
# ... (中略: milaupload.py のパート4〜6をここに配置) ...