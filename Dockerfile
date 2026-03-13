FROM python:3.10-slim

# Устанавливаем системные зависимости (FFmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Устанавливаем библиотеки Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

# Запускаем бота
CMD ["python", "bot.py"]
