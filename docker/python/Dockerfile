FROM python:3.6.2-alpine3.6

RUN apk --no-cache add bash

ENV PYTHONUNBUFFERED 1

RUN pip install --no-cache-dir \
  coverage==4.4.1 \
  websockets==3.4
