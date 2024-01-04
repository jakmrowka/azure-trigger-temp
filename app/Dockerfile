FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV UVICORN_CMD="uvicorn main:app --host 0.0.0.0 --port 30003"

EXPOSE 30003

CMD [ "sh", "-c", "$UVICORN_CMD" ]
