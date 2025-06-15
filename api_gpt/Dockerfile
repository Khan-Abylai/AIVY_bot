FROM python:3.10-slim

ENV TZ=Asia/Almaty
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV LANGUAGE=C.UTF-8

# Разрешаем сборку из репозиториев без валидной подписи
RUN printf 'Acquire::AllowInsecureRepositories "true";\nAPT::Get::AllowUnauthenticated "true";\n' \
    > /etc/apt/apt.conf.d/99allow-insecure

# Чистим кэш APT
RUN rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/*

# Устанавливаем утилиты и sqlite3
RUN apt-get update \
  && apt-get install -y --no-install-recommends debian-archive-keyring \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
       build-essential \
       curl \
       wget \
       sqlite3 \
  && rm -rf /var/cache/apt/archives/* /var/lib/apt/lists/*

# Обновляем pip
RUN pip install --no-cache-dir --upgrade pip

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    requests \
    openai \
    tiktoken \
    "transformers>=4.0.0" \
    "torch>=1.13.0" \
    "huggingface_hub[hf_xet]"

# Копируем исходники
COPY src/ /opt/api/
COPY prompts/ /opt/api/prompts

# Создаём директорию для хранения памяти и задаём права
RUN mkdir -p /opt/api/data \
    && chmod 777 /opt/api/data

WORKDIR /opt/api/

# Монтируем только data для сохранения памяти между перезапусками
VOLUME ["/opt/api/data"]

ENTRYPOINT ["sh", "entrypoint.sh"]
