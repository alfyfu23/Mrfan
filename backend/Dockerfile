FROM python:3.11

ENV CLEAR_DB=True

ENV DEPLOY=1

WORKDIR /app

COPY . /app

RUN mkdir -p /app/data
RUN chmod 775 /app/data

RUN pip install --no-cache-dir -i https://pypi-cache-sepi.app.secoder.net/simple -r requirements.txt

EXPOSE 80

CMD ["bash", "start.sh"]
