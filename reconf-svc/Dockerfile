FROM python:3.8.10

COPY ./.pip-pin/install.txt install.txt
RUN pip install -r install.txt

COPY . /reconf-svc
WORKDIR /reconf-svc
CMD pip install -e . && uvicorn reconf:app --reload --host 0.0.0.0 --port 80

EXPOSE 80
