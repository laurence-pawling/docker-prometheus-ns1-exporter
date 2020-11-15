FROM alpine:3.5

ENTRYPOINT ["python", "-m", "exporter"]
EXPOSE 9198
ENV FLASK_APP=/exporter/exporter/app.py \
    SERVICE_PORT=9198

RUN LAYER=build \
  && apk add -U python py-pip \
  && pip install prometheus_client delorean requests apscheduler Flask \
  && rm -rf /var/cache/apk/* \
  && rm -rf ~/.cache/pip

ADD ./exporter /exporter

LABEL container.name=laurence-pawling/prometheus-ns1-exporter:1.1.1
