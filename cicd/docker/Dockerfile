FROM python:3.6.8

WORKDIR /opt/application

COPY common /opt/application/common
COPY tasks /opt/application/tasks

RUN apt-get update && apt-get install -y ffmpeg

RUN mkdir /opt/build /tmp/storage \
 && pip install -r /opt/application/tasks/requirements.txt -b /opt/build \
 && rm -rf /opt/build

RUN chmod 777 /opt/application /tmp/storage

ENTRYPOINT ["celery", "-A", "tasks.app.celery_app"]
