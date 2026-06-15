FROM python:3.11-slim

ENV CLEAR_DB=False
ENV DEPLOY=1

WORKDIR /app

COPY . /app

RUN mkdir -p /app/data && chmod 775 /app/data

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

CMD ["bash", "start.sh"]
