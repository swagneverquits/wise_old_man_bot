FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY reddit_reply_bot ./reddit_reply_bot
COPY config ./config

RUN mkdir -p /app/data

CMD ["python", "-m", "reddit_reply_bot", "--loop", "--interval-seconds", "120", "--limit", "200", "--startup-limit", "1000"]
