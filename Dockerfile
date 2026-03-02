FROM python:3.11-slim

WORKDIR /app
COPY . /app

ENV PYTHONUNBUFFERED=1
ENV PORT=3000

EXPOSE 3000

CMD ["python3", "server.py"]
