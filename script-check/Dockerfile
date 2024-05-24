FROM python:3.9-slim

# RUN apt-get update && apt-get install -y logrotate

COPY ./common/ /app
COPY ./script-check/ /app
# COPY ./script-check/logrotate-conf /etc/logrotate.d/

RUN pip install --upgrade pip
RUN pip install -r /app/requirements.txt

WORKDIR /app

CMD ["python", "check.py"]