SHELL := /bin/bash
.SHELLFLAGS := -exuo pipefail -O globstar -c

TAG := $(shell git describe --tags `git rev-list --tags --max-count=1`)
VERSION := $(TAG:%=%)
PROJECT := "platsec-lambda-prowler-manager"
PYTHON_TEST_PATTERN ?= "*_?test.py" # Default to all types of tests
PYTHON_COVERAGE_MIN = 90 # %
PYTHON_VERSION = $(shell head -1 .python-version)
LAMBDA_NAME := platsec-lambda-prowler-manager


.PHONY: coverage-check
coverage-check: python-coverage-only

.PHONY: test
test: python-unit-test python-integration-test deployment-test

.PHONY: python-test
python-test:
	@pipenv run coverage run \
		--append \
		--branch \
		--omit "*_?test.py,*venv/*" \
		--module unittest \
			discover \
			--verbose \
			--start-directory "test" \
			--pattern $(PYTHON_TEST_FILE)$(PYTHON_TEST_PATTERN)

.PHONY: python-unit-test
python-unit-test:
	@$(MAKE) python-test PYTHON_TEST_PATTERN="*_utest.py" PYTHON_TEST_FILE=$(PYTHON_TEST_FILE)

.PHONY: python-integration-test
python-integration-test:
	@$(MAKE) python-test PYTHON_TEST_PATTERN="*_itest.py" PYTHON_TEST_FILE=$(PYTHON_TEST_FILE)

.PHONY: setup
setup:
	pip install pipenv==2020.11.15
	pipenv sync --dev

.PHONY: python-coverage-only
python-coverage-only:
	pipenv run coverage run -m unittest discover -s ./test -p '*test.py'
	pipenv run coverage run -m unittest discover -s ./deployment_scripts/test -p '*test.py'
	pipenv run coverage report --fail-under $(PYTHON_COVERAGE_MIN)

.PHONY: python-coverage
python-coverage:
	-@rm .coverage
	@$(MAKE) python-unit-test
	@$(MAKE) python-integration-test
	@$(MAKE) deployment-unit-test
	@$(MAKE) deployment-integration-test
	@$(MAKE) python-coverage-only

.PHONY: deployment-test
deployment-test:
	@$(MAKE) deployment-unit-test
	@$(MAKE) deployment-integration-test

.PHONY: deployment-unit-test
deployment-unit-test:
	pipenv run python -m unittest discover -s ./deployment_scripts/test -p '*_utest.py'

.PHONY: deployment-integration-test
deployment-integration-test:
	pipenv run python -m unittest discover -v -s ./deployment_scripts/test -p '*_itest.py'

.PHONY: generate-sha256
generate-sha256:
	@openssl dgst -sha256 -binary ./build-target/${LAMBDA_NAME}-${VERSION}.zip \
	| openssl enc -base64 > ./build-target/${LAMBDA_NAME}-${VERSION}.zip.base64sha256

.PHONY: publish-sandbox
publish-sandbox: package generate-sha256
	@aws s3 cp \
		./build-target/${LAMBDA_NAME}-${VERSION}.zip \
		s3://platsec-deployment-artifacts-sandbox-93bc63e0b4/${LAMBDA_NAME}-${VERSION}.zip \
		--acl=bucket-owner-full-control --content-type application/zip

	@aws s3 cp \
		./build-target/${LAMBDA_NAME}-${VERSION}.zip.base64sha256 \
		s3://platsec-deployment-artifacts-sandbox-93bc63e0b4/${LAMBDA_NAME}-${VERSION}.zip.base64sha256 \
		--acl=bucket-owner-full-control \
		--content-type application/zip

.PHONY: publish-development
publish-development: package generate-sha256
	@aws s3 cp \
		./build-target/${LAMBDA_NAME}-${VERSION}.zip \
		s3://platsec-deployment-artifacts-development-759b74ce43/${LAMBDA_NAME}-${VERSION}.zip \
		--acl=bucket-owner-full-control --content-type application/zip

	@aws s3 cp \
		./build-target/${LAMBDA_NAME}-${VERSION}.zip.base64sha256 \
		s3://platsec-deployment-artifacts-development-759b74ce43/${LAMBDA_NAME}-${VERSION}.zip.base64sha256 \
		--acl=bucket-owner-full-control \
		--content-type application/zip

.PHONY: publish-production
publish-production: package generate-sha256
	@aws s3 cp \
		./build-target/${LAMBDA_NAME}-${VERSION}.zip \
		s3://platsec-deployment-artifacts-production-fd89784e59/${LAMBDA_NAME}-${VERSION}.zip \
		--acl=bucket-owner-full-control --content-type application/zip
	@aws s3 cp \
		./build-target/${LAMBDA_NAME}-${VERSION}.zip.base64sha256 \
		s3://platsec-deployment-artifacts-production-fd89784e59/${LAMBDA_NAME}-${VERSION}.zip.base64sha256 \
		--acl=bucket-owner-full-control \
		--content-type application/zip


.PHONY: pr-for-%
pr-for-%:
	@pipenv run python deployment_scripts/release_terraform_pr.py --base ${*} --version "${VERSION}" --project ${PROJECT}

package:
	if ! [ -d "build-target" ]; then mkdir build-target; fi
	zip build-target/${LAMBDA_NAME}-${VERSION}.zip platsec_lambda_prowler_manager.py data/* lib/* account_configs.json
	mkdir -p dist
	pipenv lock -r > dist/requirements.txt
	pipenv run pip install --no-cache-dir -r dist/requirements.txt --target dist/
	cd dist && zip -r ../build-target/${LAMBDA_NAME}-${VERSION}.zip .
