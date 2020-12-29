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
        for zone,qps in dns_data.iteritems():
            families['ns1_dns_qps'].add_metric(
                [zone], qps)

    families = {
        'ns1_dns_qps': GaugeMetricFamily(
            'ns1_dns_zone_qps',
            'DNS QPS per zone',
            labels=[
                'zone'
            ]
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
