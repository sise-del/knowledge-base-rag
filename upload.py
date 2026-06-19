import os
import sys
import boto3
from datetime import datetime, timezone

# ==========================================
# 保存先URLを設定
# ==========================================
bucket_name = 'rag-document-535179725289-ap-northeast-1-an'
s3_folder = 'TEST/' 

# AWS S3のクライアントを作成
s3 = boto3.client('s3')

# スクリプトファイルが置いてあるフォルダの絶対パスを自動取得
local_folder = os.path.dirname(os.path.abspath(__file__))

print(f"[{datetime.now()}] 同期処理を開始します。")

# ------------------------------------------
# 1. S3上の既存ファイル情報を一括取得（差分比較用）
# ------------------------------------------
print("S3上の既存ファイル情報を取得中...")
s3_files = {}
try:
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name, Prefix=s3_folder):
        if 'Contents' in page:
            for obj in page['Contents']:
                # キー（S3上のパス）を元に、サイズと最終更新日時を記録
                s3_files[obj['Key']] = {
                    'Size': obj['Size'],
                    'LastModified': obj['LastModified']
                }
except Exception as e:
    print(f"S3情報の取得中にエラーが発生しました（処理は続行します）: {e}")

# ------------------------------------------
# 2. ローカルファイルをスキャンしてアップロード
# ------------------------------------------
print(f"ローカルのフォルダ [{local_folder}] 内をスキャン中...")

uploaded_count = 0
skipped_count = 0

for root, dirs, files in os.walk(local_folder):
    # '.' で始まる隠しフォルダ（.git など）を探索対象から完全に除外
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    
    for file in files:
        # '.' で始まる隠しファイル（.gitignore や .DS_Store など）も除外
        if file.startswith('.'):
            continue
            
        # このスクリプト自身のファイル（例: upload.py）はアップロード対象から除外
        if file == os.path.basename(__file__):
            continue
            
        local_path = os.path.join(root, file)
        
        # ローカルの相対パスを計算し、S3上の保存パスを作成
        relative_path = os.path.relpath(local_path, local_folder)
        s3_key = os.path.join(s3_folder, relative_path).replace("\\", "/")
        
        # --- 差分チェックロジック ---
        local_size = os.path.getsize(local_path)
        local_mtime = os.path.getmtime(local_path)
        # S3のタイムゾーン(UTC)に合わせてローカルの更新日時を変換
        local_dt = datetime.fromtimestamp(local_mtime, timezone.utc)
        
        # すでにS3に同じファイルが存在する場合
        if s3_key in s3_files:
            s3_meta = s3_files[s3_key]
            
            # 「サイズが同じ」かつ「ローカルの更新日時がS3の更新日時より古い（または同じ）」ならスキップ
            # ※S3のLastModifiedはアップロードした日時になるため、ローカル側がそれより新しくない限り変更なしと判定します
            if local_size == s3_meta['Size'] and local_dt <= s3_meta['LastModified']:
                skipped_count += 1
                continue
        # ----------------------------

        try:
            print(f"アップロード中: {s3_key}")
            s3.upload_file(local_path, bucket_name, s3_key)
            uploaded_count += 1
        except Exception as e:
            print(f"エラー発生 ({s3_key}): {e}")

print(f"[{datetime.now()}] すべての処理が完了しました！ (アップロード: {uploaded_count}件 / スキップ: {skipped_count}件)")