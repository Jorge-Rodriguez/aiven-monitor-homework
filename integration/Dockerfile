FROM ubuntu:latest

RUN apt update
RUN apt install -y python3-pip

copy . /code

WORKDIR /code

RUN pip3 install pytest psycopg2-binary
