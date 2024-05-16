FROM python:3.9-slim

COPY ./common/ /app
COPY ./tg-sender/ /app
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

WORKDIR /app

CMD ["python", "sender.py"]