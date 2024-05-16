FROM python:3.9-slim

COPY ./common/ /app
COPY ./script-parse/ /app
RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

WORKDIR /app

CMD ["python", "parse.py"]