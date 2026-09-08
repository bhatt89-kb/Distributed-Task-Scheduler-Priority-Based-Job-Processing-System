FROM python:3.12-slim

WORKDIR /app

COPY basic.py .

CMD ["python", "basic.py"]