PYTHON = $(shell which python3 || which python)
PIP = $(shell which pip3 || which pip)
PIP_COMPILE = $(shell which pip-compile)

run:
	if [ ! -d storage]; then \
	  mkdir storage; \
	fi; \
	docker-compose up

worker:
	env CONFIG='tasks.config' MODE='dev' celery -A tasks.app.celery_app worker --pool=solo -c1
beat:
	env CONFIG='tasks.config' MODE='dev' celery -A tasks.app.celery_app beat


unittests-common:
	env CONFIG='common.tests.config' ${PYTHON} -m pytest common/tests
unittests-tasks:
	env CONFIG='tasks.config' ${PYTHON} -m pytest tasks/tests
unittests: unittests-common unittests-tasks


common.requirements-dev.txt: common/requirements-dev.in
	env LC_ALL=en_US.utf8 ${PIP_COMPILE} -o - common/requirements-dev.in > common/requirements-dev.txt
tasks.requirements.txt: tasks/requirements.in
	env LC_ALL=en_US.utf8 ${PIP_COMPILE} -o - tasks/requirements.in > tasks/requirements.txt
tasks.requirements-dev.txt: tasks/requirements-dev.in
	env LC_ALL=en_US.utf8 ${PIP_COMPILE} -o - tasks/requirements-dev.in > tasks/requirements-dev.txt

py3-install-common-dev:
	${PIP} install -r common/requirements-dev.txt
py3-install-tasks:
	${PIP} install -r tasks/requirements.txt
py3-install-tasks-dev:
	${PIP} install -r tasks/requirements-dev.txt


deps-common: py3-install-common-dev
deps-tasks: py3-install-tasks py3-install-tasks-dev


deps: deps-common deps-tasks


lint:
	flake8 --config flake8.ini .


tests: lint unittests


py3-install-flake:
	${PIP} install flake8==3.7.8
