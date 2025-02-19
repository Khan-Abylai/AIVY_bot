build_api_gpt:
	docker build -t doc.aivy.kz/api_gpt:app api_gpt/

build_bot:
	docker build -t doc.aivy.kz/telegram_bot:app telegram/

build_all:
	make build_api_gpt
	make build_bot

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
