import os
import sys
import subprocess
import shutil
import getpass

os.environ["PATH"] += os.pathsep + r"C:\Users\s_ise\Desktop\調査用\knowledge-base-rag\ffmpeg-2026-06-15-git-44d082edc8-essentials_build\bin"

try:
    from moviepy import VideoFileClip
    import whisper
except ImportError as e:
    print(f"【エラー】ライブラリの読み込みに失敗しました: {e}")
    print("コマンドプロンプトで以下を実行してください：\npip install moviepy openai-whisper")
    exit(1)

# ==========================================
# 1. 自動設定
# ==========================================
username = getpass.getuser()

if len(sys.argv) > 1:
    TARGET_DIR = os.path.abspath(sys.argv[1])
else:
    TARGET_DIR = f"C:\\Users\\{username}\\Desktop\\ナレッジ変換"

OUTPUT_BASE_DIR = os.path.join(TARGET_DIR, "変換後")
# ★ trash_backup の設定を削除しました

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
        return

    if not os.path.exists(LIBREOFFICE_PATH):
        print(f"【エラー】LibreOfficeが見つかりません: {LIBREOFFICE_PATH}")
        return

    print("-> 文字起こしAI (Whisper) を初期化中...")
    model = whisper.load_model("base")

    print(f"\n--- 変換＆文字起こし処理を開始します ---")
    print(f"対象フォルダ: {target_path}")
    print(f"出力先フォルダ: {OUTPUT_BASE_DIR}\n")

    for root, dirs, files in os.walk(target_path):
        # 「変換後」フォルダ自体を検索対象から除外（無限ループ防止）
        dirs[:] = [d for d in dirs if d != '変換後' and not d.startswith('.')]

        relative_path = os.path.relpath(root, target_path)
        current_output_dir = os.path.abspath(os.path.join(OUTPUT_BASE_DIR, relative_path))

        for file in files:
            file_path = os.path.join(root, file)
            file_name = file
            file_lower = file_name.lower()

            if file_name.startswith('~$') or file_name.startswith('.~lock.'):
                continue

            if file_name == "clean_local_folders.py":
                continue

            # 成果物のチェック用に拡張子を除いたファイル名を取得
            base_name, _ = os.path.splitext(file_name)

            # ----------------------------------------------------
            # ① Excel / パワポを見つけたらPDF変換
            # ----------------------------------------------------
            if file_lower.endswith(OFFICE_EXTENSIONS):
                # ★追加：すでに変換後のPDFが存在するならスキップ
                expected_pdf = os.path.join(current_output_dir, base_name + ".pdf")
                if os.path.exists(expected_pdf):
                    print(f"   -> [スキップ] すでにPDFが存在します: {file_name}")
                    continue

                print(f"【PDF変換】Officeファイルを変換します: {file_name}")
                convert_to_pdf_local(file_path, current_output_dir)
                # ★ move_to_trash の呼び出しを削除しました
                continue

            # ----------------------------------------------------
            # ② 動画 / 音声を見つけたら文字起こし
            # ----------------------------------------------------
            if file_lower.endswith(VIDEO_EXTENSIONS):
                # ★追加：すでに文字起こしテキストが存在するならスキップ
                expected_txt = os.path.join(current_output_dir, base_name + ".txt")
                if os.path.exists(expected_txt):
                    print(f"   -> [スキップ] すでにテキストが存在します: {file_name}")
                    continue

                print(f"【文字起こし】動画/音声をテキスト化します: {file_name}")
                transcribe_video(file_path, model, current_output_dir)
                # ★ move_to_trash の呼び出しを削除しました
                continue

# ==========================================
# 3. 変換・文字起こし用関数
# ==========================================
def convert_to_pdf_local(file_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    cmd = [LIBREOFFICE_PATH, "--headless", "--convert-to", "pdf", "--outdir", output_dir, file_path]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("   -> [成功] PDFが生成されました。")
        return True
    except Exception as e:
        print(f"   -> [失敗] PDF変換エラー: {e}")
        return False

def transcribe_video(file_path, model, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    
    base_name, ext = os.path.splitext(os.path.basename(file_path))
    audio_path = os.path.join(output_dir, base_name + "_temp.mp3")
    txt_path = os.path.join(output_dir, base_name + ".txt")
    
    try:
        if ext.lower() == '.mp4':
            video = VideoFileClip(file_path)
            if video.audio is None:
                print("   -> [スキップ] 音声が含まれていない動画です。")
                return False
            video.audio.write_audiofile(audio_path, logger=None)
            target_audio = audio_path
        else:
            target_audio = file_path

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

# ★ move_to_trash 関数自体を削除しました

if __name__ == "__main__":
    clean_folder(TARGET_DIR)
    print("\n--- すべての処理が完了しました！ ---")