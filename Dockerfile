FROM python:3.12-slim

WORKDIR /app
COPY . /app

EXPOSE 4000
ENV PORT=4000
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
