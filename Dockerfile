FROM python:3.11-slim

# نصب ابزارهای لازم
RUN apt-get update && apt-get install -y ffmpeg git cmake build-essential wget ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
COPY bot.py .
COPY .env.example .env

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# بیلد کردن whisper.cpp (ممکن است زمان‌بر باشد)
RUN git clone https://github.com/ggerganov/whisper.cpp.git /tmp/whisper.cpp && \
    cd /tmp/whisper.cpp && \
    cmake -B build && cmake --build build -j && \
    cp build/bin/* /usr/local/bin/ || true

# دانلود مدل ggml-small (اگر URL در زمان دپلوی تغییر کند ممکن است نیاز به اصلاح باشد)
RUN mkdir -p /app/models && \
    wget -O /app/models/ggml-small.bin "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin" || true

CMD ["python", "bot.py"]
