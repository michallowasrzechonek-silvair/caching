SERVICES=bff projects commissioning

lint: $(foreach SVC,$(SERVICES),$(SVC)-lint)
format: $(foreach SVC,$(SERVICES),$(SVC)-format) tests-format

tests-format:
	black tests
	isort tests

$(foreach SVC,$(SERVICES),$(SVC)-format): %-format:
	@cd $*-svc && \
	black $* && \
	isort $*

$(foreach SVC,$(SERVICES),$(SVC)-lint): %-lint:
	@cd $*-svc && \
	flake8 $* && \
	mypy $*
