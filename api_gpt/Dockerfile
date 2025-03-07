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
    openai==0.28.0 \
    sentence-transformers \
    qdrant-client \
    nest_asyncio

COPY src/ /opt/api/
WORKDIR /opt/api/
ENV PYTHONPATH="/opt/api/"

ENTRYPOINT ["sh", "entrypoint.sh"]
