FROM python:3.10-slim

# Настройка часового пояса
ENV TZ=Asia/Almaty
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Локаль
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV LANGUAGE=C.UTF-8

# Установка системных зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Обновление pip
RUN pip install --no-cache-dir --upgrade pip

# Установка python-зависимостей
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    requests \
    openai

# Копирование исходного кода в контейнер
ADD src/ /opt/api/
WORKDIR /opt/api/

# ENTRYPOINT: запускаем стартовый скрипт (например, для запуска uvicorn)
ENTRYPOINT ["sh", "entrypoint.sh"]
