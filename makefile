export PYTHONASYNCIODEBUG=1
export PYTHONWARNINGS=default
SHELL=/bin/bash
usr := $(shell id -u):$(shell id -g)

.PHONY: test coverage doc build gencerts example

test:
	docker-compose -f docker-compose-test.yml run --rm test python -m unittest

coverage:
	docker-compose -f docker-compose-test.yml run --rm -u $(usr) test bash -c \
		" \
			python -m coverage erase \
			&& python -m coverage run \
				--branch --source=aiowstunnel --omit '*/test_*' -m unittest \
			&& python -m coverage report -m \
			&& python -m coverage html \
		"

doc:
	docker-compose -f docker-compose-test.yml run --rm -u $(usr) \
	-w /aiowstunnel/docs/ test bash -c \
		" \
			rm -rf _build && mkdir _build \
			&& sphinx-build -b html . _build \
		"

build:
	-rm -rf aiowstunnel/resources
	mkdir -p aiowstunnel/resources
	cp -r aiowstunnel/healthcheck_frontend/build/* aiowstunnel/resources/
	docker-compose -f docker-compose-develop.yml run --rm react npm run build

gencerts:
	cd examples/certificates && ./create.sh

example: build
	docker-compose -f docker-compose-example.yml up

distrbute: build
	rm dist/*
	python setup.py sdist
	twine upload dist/*
