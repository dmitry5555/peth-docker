up:
	docker compose up -d
down:
	docker compose down
restart:
	down up
build:
	docker compose build
logs:
	docker compose logs -f
reset:
	docker compose build --no-cache
# deploy:
# 	git pull && docker-compose build && docker-compose up -d