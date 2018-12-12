"""
Apptuit Pyformance Reporter
"""
from pyformance.reporters.reporter import Reporter
from apptuit import Apptuit, DataPoint, timeseries


class ApptuitReporter(Reporter):

    def __init__(self, registry=None, reporting_interval=10, token=None,
                 api_endpoint="https://api.apptuit.ai", prefix="", tags={}):
        super(ApptuitReporter, self).__init__(registry=registry,
             reporting_interval=reporting_interval)
        self.endpoint = api_endpoint
        self.metric_tags = {}
        self.token = token
        self.tags = tags
        self.prefix = prefix
        self.client = Apptuit(token, api_endpoint)

    def report_now(self, registry=None, timestamp=None):
        """
        Report the data
        Params:
            registry: pyformance Registry containing all metrics
            timestamp: timestamp of the data point
        """
        dps = self._collect_data_points(registry or self.registry, timestamp)
        if len(dps) > 0:
            self.client.send(dps)

    def _get_tags(self, key):
        """
        Get tags of a metric
        Params:
            metric key
        Returns:
            metric name, dictionary of tags
        """
        if key not in self.metric_tags.keys():
            metric_name, metric_tags = timeseries.decode_metric(key)
            self.metric_tags[key] = (metric_name, metric_tags)
        else:
            metric_name, metric_tags = self.metric_tags[key]
        return metric_name, metric_tags

    def _collect_data_points(self, registry, timestamp=None):
        """
        will collect all metrics from registry and convert them to DataPoints
        Params:
            registry: pyformance registry object
            timestamp: timestamp of the data point
        Returns:
            list of DataPoints
        """
        timestamp = timestamp or int(round(self.clock.time()))
        metrics = registry.dump_metrics()
        dps = []
        global_tags = self.tags
        for key in metrics.keys():
            metric_name, metric_tags = self._get_tags(key)
            if metric_tags:
                tags = global_tags.copy()
                tags.update(metric_tags)
            else:
                tags = global_tags
            for value_key in metrics[key].keys():
                dps.append(DataPoint(metric="{0}{1}.{2}".format(self.prefix, metric_name, value_key),
                                     tags=tags,
                                     timestamp=timestamp,
                                     value=metrics[key][value_key]))
        return dps
