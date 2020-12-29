# -*- encoding: utf-8 -*-

from __future__ import print_function

import datetime
import delorean
import os
import sys
import json
import logging

import requests
import time

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.exposition import generate_latest

from . import dnsexporter


logging.basicConfig(level=logging.os.environ.get('LOG_LEVEL', 'INFO'))


REQUIRED_VARS = {'SERVICE_PORT', 'AUTH_TOKEN'}
for key in REQUIRED_VARS:
    if key not in os.environ:
        logging.error('Missing value for %s' % key)
        sys.exit()

SERVICE_PORT = int(os.environ.get('SERVICE_PORT', 9198))
ENDPOINT = 'https://api.nsone.net/v1'
AUTH_TOKEN = os.environ.get('AUTH_TOKEN')

HEADERS = {
    'X-NSONE-Key': AUTH_TOKEN
}
HTTP_SESSION = requests.Session()


class RegistryMock(object):
    def __init__(self, metrics):
        self.metrics = metrics

    def collect(self):
        for metric in self.metrics:
            yield metric


def get_data_from_ns1(url):
    r = HTTP_SESSION.get(url, headers=HEADERS)
    return json.loads(r.content.decode('UTF-8'))


def get_zone_list():
    logging.info('Getting zones from NS1')
    r = get_data_from_ns1(url='%s/zones' % (ENDPOINT))
    zones = []
    for z in r:
        logging.debug('registered zone %s' % (z['zone']))
        zones.append(z['zone'])
    return zones


def metric_processing_time(name):
    def decorator(func):
        # @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            result = func(*args, **kwargs)
            elapsed = (time.time() - now) * 1000
            logging.debug('Processing %s took %s miliseconds' % (
                name, elapsed))
            internal_metrics['processing_time'].add_metric([name], elapsed)
            return result
        return wrapper
    return decorator


@metric_processing_time('dns')
def get_dns_metrics(zones):
    logging.info('Fetching NS1 QPS metrics data')
    endpoint = '%s/stats/qps/%s'
    zone_qps = {}
    for zone in zones:
        r = get_data_from_ns1(url=endpoint % (ENDPOINT, zone))
        if 'qps' not in r:
            logging.error('Failed to get information from NS1')
            logging.error('zone: %s, message: %s' % (zone, r['message']))
            zone_qps[zone] = ''
        else:
            logging.debug('Recorded %s QPS for zone %s' % (r['qps'], zone))
            zone_qps[zone] = int(r['qps'])

    return dnsexporter.process(zone_qps)


def update_latest():
    global latest_metrics, internal_metrics, zones
    internal_metrics = {
        'processing_time': GaugeMetricFamily(
            'ns1_exporter_processing_time_miliseconds',
            'Processing time in ms',
            labels=[
                'name'
            ]
        )
    }

    latest_metrics = (get_dns_metrics(zones))
    latest_metrics += generate_latest(RegistryMock(internal_metrics.values()))


app = Flask(__name__)


@app.route("/")
def home():
    return """<h3>Welcome to the NS1 prometheus exporter!</h3>
The following endpoints are available:<br/>
<a href="/metrics">/metrics</a> - Prometheus metrics<br/>
<a href="/status">/status</a> - A simple status endpoint returning "OK"<br/>"""


@app.route("/status")
def status():
    return "OK"


@app.route("/metrics")
def metrics():
    return latest_metrics


def run():
    global zones

    logging.info('Starting scrape service ')

    zones = get_zone_list()

    update_latest()

    scheduler = BackgroundScheduler({'apscheduler.timezone': 'UTC'})
    scheduler.add_job(update_latest, 'interval', seconds=60)
    scheduler.start()

    try:
        app.run(host="0.0.0.0", port=SERVICE_PORT, threaded=True)
    finally:
        scheduler.shutdown()
