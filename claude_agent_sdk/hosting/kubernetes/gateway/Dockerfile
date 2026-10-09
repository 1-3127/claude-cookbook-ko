FROM python:3.12-slim

WORKDIR /app

# 먼저 dependency 설치(layer caching — requirements가 바뀔 때만 재실행)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application 코드 복사(평면 구조 — sub-package 없음)
COPY main.py k8s.py proxy.py ./

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
