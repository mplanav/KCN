FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir . \
 && pip install --no-cache-dir flet flet-web fastapi "uvicorn[standard]" \
      matplotlib zxing-cpp Pillow

ENV KCN_DATA_DIR=/data
ENV KCN_INVITE_CODE=KCN-INVITA
RUN mkdir -p /data
EXPOSE 8080

CMD ["uvicorn", "serve:app", "--host", "0.0.0.0", "--port", "8080"]
