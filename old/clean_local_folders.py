import os
import subprocess
import shutil
import getpass

os.environ["PATH"] += os.pathsep + r"C:\Users\s_ise\Desktop\調査用\knowledge-base-rag\ffmpeg-2026-06-15-git-44d082edc8-essentials_build\bin"

# ====================================================================
# 【事前準備】コマンドプロンプトで以下を実行しておいてください：
# pip install moviepy openai-whisper torch
# ====================================================================
try:
    from moviepy import VideoFileClip
    import whisper
except ImportError as e:
    print(f"【エラー】ライブラリの読み込みに失敗しました: {e}")
    print("コマンドプロンプトで以下を実行してください：\npip install moviepy openai-whisper")
    exit(1)

# ==========================================
# 1. 自動設定（デスクトップの「ナレッジ変換」を自動認識します）
# ==========================================
username = getpass.getuser()
# デスクトップの「ナレッジ変換」フォルダをターゲットに設定
TARGET_DIR = f"C:\\Users\\{username}\\Desktop\\ナレッジ変換"
# 処理が終わった元ファイルを退避させるフォルダ
TRASH_DIR = f"C:\\Users\\{username}\\Desktop\\ナレッジ変換\\trash_backup"

# Windows用：LibreOfficeの標準インストールパス
LIBREOFFICE_PATH = r"C:\Program Files\LibreOffice\program\soffice.exe"

# 対象とする拡張子の定義
OFFICE_EXTENSIONS = ('.xlsx', '.xlsm', '.pptx', '.ppt')
VIDEO_EXTENSIONS = ('.mp4', '.m4a', '.mp3', '.wav')

# ==========================================
# 2. メイン処理ロジック
# ==========================================
def clean_folder(target_path):
    if not os.path.exists(target_path):
        print(f"【エラー】指定されたフォルダが見つかりません: {target_path}")
        print("デスクトップに『ナレッジ変換』という名前でフォルダが作成されているか確認してください。")
        return

    # 変換ソフトの存在チェック
    if not os.path.exists(LIBREOFFICE_PATH):
        print(f"【エラー】LibreOfficeが見つかりません: {LIBREOFFICE_PATH}")
        print("LibreOfficeが正しくインストールされているか確認してください。")
        return

    # Whisperモデルの読み込み
    print("-> 文字起こしAI (Whisper) を初期化中...")
    model = whisper.load_model("base")

    print(f"\n--- 変換＆文字起こし処理を開始します ---")
    print(f"対象フォルダ: {target_path}\n")

    # フォルダ内を全自動で探索
    for root, dirs, files in os.walk(target_path):
        # ごみ箱フォルダ(trash_backup)の中身は処理対象から除外する
        if os.path.commonpath([root, TRASH_DIR]) == TRASH_DIR:
            continue

        for file in files:
            file_path = os.path.join(root, file)
            file_name = file
            file_lower = file_name.lower()

            # 誰かが開いている時の「一時ファイル（~$...）」はスキップ
            if file_name.startswith('~$') or file_name.startswith('.~lock.'):
                continue

            # スクリプトファイル自身はスキップ
            if file_name == "clean_local_folders.py":
                continue

            # ----------------------------------------------------
            # ① Excel / パワポを見つけたらPDF変換
            # ----------------------------------------------------
            if file_lower.endswith(OFFICE_EXTENSIONS):
                print(f"【PDF変換】Officeファイルを変換します: {file_name}")
                if convert_to_pdf_local(file_path, root):
                    move_to_trash(file_path, target_path)
                continue

            # ----------------------------------------------------
            # ② 動画 / 音声を見つけたら文字起こし
            # ----------------------------------------------------
            if file_lower.endswith(VIDEO_EXTENSIONS):
                print(f"【文字起こし】動画/音声をテキスト化します: {file_name}")
                if transcribe_video(file_path, model):
                    move_to_trash(file_path, target_path)
                continue

# ==========================================
# 3. 変換・文字起こし用関数
# ==========================================
def convert_to_pdf_local(file_path, output_dir):
    """LibreOfficeを使ってその場でPDFに変換する"""
    cmd = [LIBREOFFICE_PATH, "--headless", "--convert-to", "pdf", "--outdir", output_dir, file_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("   -> [成功] PDFが生成されました。")
        return True
    except Exception as e:
        print(f"   -> [失敗] PDF変換エラー: {e}")
        return False

def transcribe_video(file_path, model):
    """動画から音声を分離し、AIで文字起こしをして同じ場所に.txtで保存する"""
    base_path, ext = os.path.splitext(file_path)
    audio_path = base_path + "_temp.mp3"
    txt_path = base_path + ".txt"
    
    try:
        if ext.lower() == '.mp4':
            video = VideoFileClip(file_path)
            if video.audio is None:
                print("   -> [スキップ] 音声が含まれていない動画です。")
                return False
            video.audio.write_audiofile(audio_path, logger=None)
            target_audio = audio_path
        else:
            target_audio = file_path # m4aはそのまま処理

        result = model.transcribe(target_audio, language="ja")
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result["text"])
        
        print(f"   -> [成功] テキストファイルを生成しました: {os.path.basename(txt_path)}")
        
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return True
    except Exception as e:
        print(f"   -> [失敗] 文字起こしエラー: {e}")
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return False

def move_to_trash(file_path, base_dir):
    """元ファイルをフォルダ構造を保ったまま退避させる"""
    try:
        relative_path = os.path.relpath(file_path, base_dir)
        dest_path = os.path.join(TRASH_DIR, relative_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.move(file_path, dest_path)
    except Exception as e:
        print(f"   -> [退避失敗]: {e}")

if __name__ == "__main__":
    clean_folder(TARGET_DIR)
    print("\n--- すべての処理が完了しました！ ---")