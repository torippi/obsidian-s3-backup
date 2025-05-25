# Python 3.11をベースイメージとして使用
FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの更新と必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    zip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係ファイルをコピー
COPY requirements.txt .

# Pythonパッケージのインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションソースコードをコピー
COPY src/ ./src/
COPY .env .env

# ログディレクトリを作成
RUN mkdir -p /app/logs

# 実行権限を設定
# RUN chmod +x src/main.py

# デフォルトのコマンドを設定
# CMD ["python", "src/main.py"]