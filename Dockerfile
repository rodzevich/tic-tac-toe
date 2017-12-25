FROM python:3.6

ADD game /app
RUN pip install -r /app/requirements.txt

WORKDIR /app
ENV PYTHONPATH /