export PYTHONASYNCIODEBUG=1
export PYTHONWARNINGS=default

usr := $(shell id -u):$(shell id -g)

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
