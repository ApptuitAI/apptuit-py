"""
Apptuit Pyformance Reporter
"""
from pyformance.reporters.reporter import Reporter
from apptuit import Apptuit, DataPoint, timeseries


class ApptuitReporter(Reporter):

    def __init__(self, registry=None, reporting_interval=10, token=None,
                 api_endpoint="https://api.apptuit.ai", prefix="", tags=None):
        super(ApptuitReporter, self).__init__(registry=registry,
                                              reporting_interval=reporting_interval)
        self.endpoint = api_endpoint
        self.token = token
        self.tags = tags
        self.prefix = prefix if prefix is not None else ""
        self.client = Apptuit(token, api_endpoint)
        self.__decoded_metrics_cache = {}

    def report_now(self, registry=None, timestamp=None):
        """
        Report the data
        Params:
            registry: pyformance Registry containing all metrics
            timestamp: timestamp of the data point
        """
        dps = self._collect_data_points(registry or self.registry, timestamp)
        if dps:
            self.client.send(dps)

    def _get_tags(self, key):
        """
        Get tags of a metric
        Params:
            metric key
        Returns:
            metric name, dictionary of tags
        """
        val = self.__decoded_metrics_cache.get(key)
        if val:
            return val[0], val[1]

        metric_name, metric_tags = timeseries.decode_metric(key)
        self.__decoded_metrics_cache[key] = (metric_name, metric_tags)
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
        global_tags = self.tags if self.tags else {}
        for key in metrics.keys():
            metric_name, metric_tags = self._get_tags(key)
            if metric_tags and global_tags:
                tags = global_tags.copy()
                tags.update(metric_tags)
            elif metric_tags:
                tags = metric_tags
            else:
                tags = global_tags
            for value_key in metrics[key].keys():
                dps.append(DataPoint(metric="{0}{1}.{2}".format(self.prefix, metric_name, value_key),
                                     tags=tags,
                                     timestamp=timestamp,
                                     value=metrics[key][value_key]))
        return dps
