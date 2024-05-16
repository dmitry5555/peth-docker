FROM python:3.9-slim

COPY ./server/ /app
WORKDIR /app

CMD ["python3", "-m", "http.server", "8080"]