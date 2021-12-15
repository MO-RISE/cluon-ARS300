FROM python:3.8-slim-bullseye

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

WORKDIR /app

COPY memo/ memo/
COPY can_database_ch0.dbc can_database_ch0.dbc
COPY main.py main.py

CMD ["python3", "main.py"]