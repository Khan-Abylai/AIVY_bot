FROM python:3.10-slim

ENV TZ=Asia/Almaty
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV LANGUAGE=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    python-multipart \
    requests \
    transformers

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

ADD src/ /opt/api/
WORKDIR /opt/api/

# Если монтировать модель как Volume:
#   VOLUME ["/models"]

ENTRYPOINT ["sh", "entrypoint.sh"]
