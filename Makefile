# Сборка образа для сервиса api (старый API)
build_api:
	docker build -t doc.smartparking.kz/lp_recognizer_api:app api/

# Сборка образа для сервиса api_gpt (новый сервис с GPT)
build_api_gpt:
	docker build -t doc.smartparking.kz/api_gpt:app api_gpt/

# Сборка образа для сервиса telegram
build_bot:
	docker build -t doc.smartparking.kz/lp_recognizer_bot:app telegram/

# Общая сборка всех образов
build_all:
	make build_api
	make build_api_gpt
	make build_bot

# Поднятие сервисов с пересборкой (если необходимо)
run:
	docker compose up -d --build

stop:
	docker compose down

restart:
	make stop
	make run

build_and_run:
	make build_all
	make run
