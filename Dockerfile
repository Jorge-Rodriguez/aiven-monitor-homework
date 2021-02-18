FROM ubuntu:latest

RUN apt update
RUN apt install -y python3-pip

COPY . /code

WORKDIR /code

RUN pip3 install pytest
RUN pip3 install -r requirements.txt

RUN pytest url_monitor
