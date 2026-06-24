import os
import sys
import boto3
from datetime import datetime, timezone

# ==========================================
# 保存先の設定
# ==========================================
bucket_name = 'rag-document-535179725289-ap-northeast-1-an'
s3_folder = 'TEST/伊勢/' 

USE_TQDM = False
if sys.stdout.isatty():
    try:
        from tqdm import tqdm
        USE_TQDM = True
    except ImportError:
        print("【提示】tqdm ライブラリをインポートできません。通常のログモードで実行します。")

s3 = boto3.client('s3')

# 引数（例: /data）があればそれをルートにする
if len(sys.argv) > 1:
    given_folder = os.path.abspath(sys.argv[1])
else:
    given_folder = "/data"

# 元のフォルダ名（例：「data」）を取得
folder_name = os.path.basename(given_folder)

# ★【修正】clean.py(JSON版)の出力仕様（/data/data）に自動追従させます
# もし /data/data フォルダがあればそこをスキャン、無ければ /data をスキャン
json_output_folder = os.path.join(given_folder, folder_name)
if os.path.exists(json_output_folder):
    local_folder = json_output_folder
elif os.path.exists(os.path.join(given_folder, "変換後")):
    local_folder = os.path.join(given_folder, "変換後")
else:
    local_folder = given_folder

print(f"[{datetime.now()}] 同期処理を開始します。")

# ------------------------------------------
# 1. S3上の既存ファイル情報を一括取得
# ------------------------------------------
print("S3上の既存ファイル情報を取得中...")
s3_files = {}
try:
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name, Prefix=s3_folder):
        if 'Contents' in page:
            for obj in page['Contents']:
                s3_files[obj['Key']] = {
                    'Size': obj['Size'],
                    'LastModified': obj['LastModified']
                }
except Exception as e:
    print(f"【エラー】S3情報の取得に失敗しました: {e}")
    exit(1)

# ------------------------------------------
# 2. ローカルファイルをスキャン
# ------------------------------------------
print(f"ローカルのフォルダ [{local_folder}] 内をスキャン中...")

tasks_to_upload = []
skipped_count = 0
local_s3_keys = set()

for root, dirs, files in os.walk(local_folder):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    
    for file in files:
        if file.startswith('.'):
            continue
            
        local_path = os.path.join(root, file)
        relative_path = os.path.relpath(local_path, local_folder)
        
        s3_key = os.path.join(s3_folder, folder_name, relative_path).replace("\\", "/")
        local_s3_keys.add(s3_key)
        
        local_size = os.path.getsize(local_path)
        local_mtime = os.path.getmtime(local_path)
        local_dt = datetime.fromtimestamp(local_mtime, timezone.utc)
        
        if s3_key in s3_files:
            s3_meta = s3_files[s3_key]
            if local_size == s3_meta['Size'] and local_dt <= s3_meta['LastModified']:
                skipped_count += 1
                continue
        
        tasks_to_upload.append((local_path, s3_key))

# ------------------------------------------
# 3. 削除対象ファイルのリストアップ
# ------------------------------------------
tasks_to_delete = []
s3_root = f"{s3_folder}{folder_name}/".replace("//", "/")

for s3_key in s3_files.keys():
    if s3_key.endswith('/'):
        continue
        
    if not s3_key.startswith(s3_root):
        continue
        
    relative_s3_path = s3_key[len(s3_root):]
    if "/" not in relative_s3_path:
        continue
        
    if s3_key not in local_s3_keys:
        tasks_to_delete.append(s3_key)

# ------------------------------------------
# 4. アップロード処理の実行
# ------------------------------------------
uploaded_count = 0
if tasks_to_upload:
    if USE_TQDM:
        for local_path, s3_key in tqdm(tasks_to_upload, desc="アップロード中", unit="file"):
            try:
                s3.upload_file(local_path, bucket_name, s3_key)
                uploaded_count += 1
            except Exception as e:
                tqdm.write(f"エラー発生 ({s3_key}): {e}")
    else:
        print(f"アップロード対象: {len(tasks_to_upload)} 件")
        for local_path, s3_key in tasks_to_upload:
            try:
                print(f"アップロード中: {s3_key}")
                s3.upload_file(local_path, bucket_name, s3_key)
                uploaded_count += 1
            except Exception as e:
                print(f"エラー発生 ({s3_key}): {e}")
else:
    print("アップロードが必要な新規・更新ファイルはありません。")

# ------------------------------------------
# 5. 削除処理の実行
# ------------------------------------------
deleted_count = 0
if tasks_to_delete:
    if USE_TQDM:
        for s3_key in tqdm(tasks_to_delete, desc="不要ファイルの削除中", unit="file"):
            try:
                s3.delete_object(Bucket=bucket_name, Key=s3_key)
                deleted_count += 1
            except Exception as e:
                tqdm.write(f"削除エラー発生 ({s3_key}): {e}")
    else:
        print(f"削除対象（ローカルにないファイル）: {len(tasks_to_delete)} 件")
        for s3_key in tasks_to_delete:
            try:
                print(f"S3から削除中: {s3_key}")
                s3.delete_object(Bucket=bucket_name, Key=s3_key)
                deleted_count += 1
            except Exception as e:
                print(f"削除エラー発生 ({s3_key}): {e}")
else:
    print("S3側に削除すべき古いファイルはありません。")

print(f"[{datetime.now()}] すべての処理が完了しました！")
print(f"  - アップロード成功: {uploaded_count} / {len(tasks_to_upload)} 件")
print(f"  - スキップ(変更なし): {skipped_count} 件")
print(f"  - S3から同期削除: {deleted_count} / {len(tasks_to_delete)} 件")