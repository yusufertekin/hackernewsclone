FROM python:3
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y \
  libyaml-dev \
  vim \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /code
COPY ./requirements/ /code/requirements/
RUN pip install -r requirements/dev.txt
COPY . /code/
