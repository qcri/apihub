.PHONY: init
init:
	poetry env use $(shell pyenv which python) && \
	poetry install

.PHONY: pytest
pytest:
	poetry run pytest -vv $(ARGS)

.PHONY: test
test:
	poetry run pytest $(ARGS)

.PHONY: pdb
pdb:
	poetry run pytest --pdb $(ARGS)

.PHONY: mypy
mypy: 
	poetry run mypy --ignore-missing-imports apihub

.PHONY: result
result:
	PYTHONPATH=../pipeline/src poetry run python apihub/result.py \
		--in-kind FILE --in-filename tests/fixtures/result_input.txt \
		--out-kind FILE --out-filename - \
		--debug

.PHONY: redis-result
redis-result:
	PYTHONPATH=../pipeline/src poetry run python apihub/result.py \
	  --in-kind LREDIS --in-redis redis://localhost:6379/1 \
		--in-topic result --in-namespace apihub \
		--debug

.PHONY: server
server:
	PYTHONPATH=../pipeline/src poetry run python apihub/server.py \
		--out-kind LREDIS --debug

.PHONY: pre-commit
pre-commit: 
	pre-commit run --all-files

.PHONY: clean
clean:
	find . -name '__pycache__' -exec rm -rf {} +
