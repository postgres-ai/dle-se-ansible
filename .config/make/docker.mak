## —— Docker —————————————————————————————————————————————————————————————————————————————————————
.PHONY: docker-build
docker-build: ## Run docker build image in local
	docker build --tag dle-se-ansible:local --file Dockerfile .

.PHONY: docker-lint
docker-lint: ## Run hadolint command to lint Dokerfile
	docker run --rm -i hadolint/hadolint < Dockerfile

.PHONY: docker-tests
docker-tests: ## Run tests for docker
	$(MAKE) docker-lint
	$(MAKE) docker-build
