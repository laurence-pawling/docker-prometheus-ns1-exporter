#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.exposition import generate_latest


def process(raw_data):
    class RegistryMock(object):
        def __init__(self, metrics):
            self.metrics = metrics

        def collect(self):
            for metric in self.metrics:
                yield metric

    def generate_metrics(dns_data, families):
        for zone,qps in dns_data['qps'].iteritems():
            families['ns1_dns_qps'].add_metric(
                [zone], qps)
        for entry in dns_data['pulsar']:
            families['ns1_pulsar_decisions_count'].add_metric(
                [entry['jobid'], entry['name']], entry['value'], entry['timestamp'])

    families = {
        'ns1_dns_qps': GaugeMetricFamily(
            'ns1_dns_zone_qps',
            'DNS QPS per zone',
            labels=[
                'zone'
            ]
        ),
        'ns1_pulsar_decisions_count': GaugeMetricFamily(
            'ns1_pulsar_decisions_count',
            'NS1 Pulsar Decisions',
            labels=['pulsar_job_id','pulsar_job_name']
        )
    }

    generate_metrics(raw_data, families)
    return generate_latest(RegistryMock(families.values()))


if __name__ == "__main__":
    import os

    source_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(source_dir, "sample-dns")

    with open(path) as f:
        print process(json.load(f)['result'])
