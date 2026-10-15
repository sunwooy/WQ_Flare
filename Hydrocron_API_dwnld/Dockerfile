FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY Hydrocron_API_dwnld.py .

CMD ["python", "Hydrocron_API_dwnld.py"]