FROM python:3.8.10

ENV PIP_EXTRA_INDEX_URL=http://pypi.silvair.lan
ENV PIP_TRUSTED_HOST=pypi.silvair.lan

COPY ./.pip-pin/install.txt install.txt
RUN pip install -r install.txt

COPY . /commissioning-svc
WORKDIR /commissioning-svc
CMD pip install -e . && uvicorn commissioning:app --reload --host 0.0.0.0 --port 80

EXPOSE 80
