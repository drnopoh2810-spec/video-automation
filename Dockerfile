FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

EXPOSE 7860

CMD ["python", "app.py"]
