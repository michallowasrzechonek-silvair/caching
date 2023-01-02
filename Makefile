SERVICES=bff projects commissioning

lint: $(foreach SVC,$(SERVICES),$(SVC)-lint)
format: $(foreach SVC,$(SERVICES),$(SVC)-format)

$(foreach SVC,$(SERVICES),$(SVC)-format): %-format:
	@cd $*-svc && \
	black $* && \
	isort $*

$(foreach SVC,$(SERVICES),$(SVC)-lint): %-lint:
	@cd $*-svc && \
	flake8 $* && \
	mypy $*
