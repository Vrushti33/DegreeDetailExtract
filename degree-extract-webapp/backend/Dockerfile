FROM python:3.11-slim

WORKDIR /app

# torch's CPU wheel is large; installing it separately from a pinned index
# keeps the image smaller and the build more reliable than a bare pip install
RUN pip install --no-cache-dir torch==2.2.2 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
