.DEFAULT_GOAL := help

# --- Docker backend -------------------------------------------------------

.PHONY: db
db: ## Start Postgres+pgvector only (container DB)
	docker compose up -d postgres

.PHONY: stack
stack: ## Start Postgres+pgvector AND the local LLM container
	docker compose --profile llm up -d

.PHONY: down
down: ## Stop all containers (data volumes persist)
	docker compose down

.PHONY: logs
logs: ## Follow container logs (e.g. the LLM model download)
	docker compose logs -f

# --- Backend switch (container <-> LAN/remote) ----------------------------
# The actual switch is which endpoints .env points at. These targets swap .env
# in/out, backing up the current one to .env.bak so nothing is lost.

.PHONY: backend-docker
backend-docker: ## Point .env at the container DB + LLM (.env.docker.example)
	@[ -f .env ] && cp .env .env.bak && echo "Backed up .env -> .env.bak" || true
	cp .env.docker.example .env
	@echo "Now using the CONTAINER backend. Run: make stack"

.PHONY: backend-lan
backend-lan: ## Restore your previous .env (LAN/remote backend) from .env.bak
	@[ -f .env.bak ] || { echo "No .env.bak to restore"; exit 1; }
	cp .env.bak .env
	@echo "Restored .env from .env.bak (LAN/remote backend)."

# --- App / data -----------------------------------------------------------

.PHONY: ingest
ingest: ## Ingest the configured corpus (CORPUS_SOURCES)
	uv run corpus-rag ingest

.PHONY: app
app: ## Run the Streamlit UI
	uv run streamlit run src/corpus_rag/app.py

# --- Tests ----------------------------------------------------------------

.PHONY: test
test: ## Offline test suite (no services; what CI runs)
	uv run pytest -m "not live"

.PHONY: test-live
test-live: ## Live test suite (needs DB + LLM up and a corpus ingested)
	uv run pytest -m live -rs

.PHONY: help
help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
