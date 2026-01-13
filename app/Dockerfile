FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY monitor.py yc_api.py ./

CMD ["python", "-u", "monitor.py"]
