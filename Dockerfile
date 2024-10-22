FROM python:3.11

WORKDIR /app

COPY ./requirements.txt /app
RUN pip install -r /app/requirements.txt

COPY ./api /app/api
COPY ./controllers.py /app/controllers.py
COPY ./models.py /app/models.py
COPY ./config.py /app/config.py
COPY ./gunicorn_conf.py /app/gunicorn_conf.py
COPY ./main.py /app/main.py

CMD ["gunicorn", "-c", "gunicorn_conf.py", "main:app"]