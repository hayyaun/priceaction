.PHONY: help up down restart logs clean run

help:
	@echo "BTC/USDT Trading Bot - Docker"
	@echo ""
	@echo "  make up          - Start bot"
	@echo "  make down        - Stop bot"
	@echo "  make restart     - Restart bot"
	@echo "  make logs        - View logs"
	@echo "  make run         - Deploy (pull + build + up)"
	@echo "  make clean       - Remove all"

up:
	@echo ".> Starting bot..."
	@if [ ! -f .env ]; then \
		cp config.example.env .env; \
		echo "⚠ Edit .env with your API keys first!"; \
		exit 1; \
	fi
	docker-compose up -d --build
	@echo "✓ Bot running"

down:
	@echo ".> Stopping bot..."
	docker-compose down
	@echo "✓ Bot stopped"

restart: down up
	@echo "✓ Bot restarted"

logs:
	@docker-compose logs -f trading-bot

clean: down
	@echo ".> Cleaning..."
	-docker rmi btc-trading-bot:latest
	@echo "✓ Done"

run:
	@echo ".> Deploying..."
	git pull
	$(MAKE) down
	$(MAKE) up
	$(MAKE) logs