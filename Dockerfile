(
echo FROM python:3.11-slim
echo.
echo RUN apt-get update ^&^& apt-get install -y --no-install-recommends ^
echo     libreoffice-writer ^
echo     fonts-liberation ^
echo     fonts-noto-core ^
echo     ^&^& apt-get clean ^
echo     ^&^& rm -rf /var/lib/apt/lists/*
echo.
echo WORKDIR /app
echo.
echo COPY requirements.txt .
echo RUN pip install --no-cache-dir -r requirements.txt
echo.
echo COPY main.py index.html ./
echo.
echo EXPOSE 8000
echo.
echo CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
) > Dockerfile