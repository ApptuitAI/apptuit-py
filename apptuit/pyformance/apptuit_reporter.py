"""
Client module for Apptuit Pyformance Reporter
"""
from json import loads, dumps
from pyformance.reporters.reporter import Reporter
from apptuit import Apptuit, DataPoint


class ApptuitReporter(Reporter):

    def __init__(self, registry=None, reporting_interval=10, token=None, host="https://api.apptuit.ai",
                 prefix="", tags=None):
        super(ApptuitReporter, self).__init__(registry=registry,
                                              reporting_interval=reporting_interval)
        self.host = host
        self.metric_tags = {}
        self.token = token
        self.tags = tags
        self.prefix = prefix
        self.client = Apptuit(token, host)

    def report_now(self, registry=None, timestamp=None):
        """
        This function will be report the data.
        :param registry: pyformance Registry containing all metrics
        :param timestamp: timestamp of data point belongs to
        :return: None
        """
        dps = self._collect_data_points(registry or self.registry, timestamp)
        if len(dps) > 0:
            self.client.send(dps)

    def encode_metric_name(self, metric_name, metric_tags):
        """
        This function will return a metric which will concat the metric name with its tags
        :param metric_name: str object name of metric
        :param metric_tags: dict object tags of metric
        :return: string with metric name and its tags
        """
        if isinstance(metric_tags, dict) and isinstance(metric_name, str) and metric_name != "":
            encoded_metric_name = metric_name + dumps(metric_tags,sort_keys=True)
            return encoded_metric_name
        else:
            msg = ""
            if not isinstance(metric_name, str):
                msg += "Metric name have to be a string,"
            else:
                if metric_name == "":
                    msg += "Metric name cant be empty,"
            if not isinstance(metric_tags, dict):
                msg += "Tags have must be dictionary."
            raise ValueError(msg)

    def decode_metric_name(self, encoded_metric_name):
        """
        this will return tags of a metric when encoded format is given
        :param encoded_metric_name: a string with matric name followed by its tags
                example: 'metricName {"metricTagKey1":"metricValue1","metricTagKey2":"metricValue2"}'
        :return:
        """
        if encoded_metric_name is None or encoded_metric_name == "":
            raise ValueError("Invalid metric encode format")
        if encoded_metric_name not in self.metric_tags.keys():
            isthere = encoded_metric_name.find('{')
            if isthere > -1:
                try:
                    metric_tags = loads(encoded_metric_name[isthere:])
                    metric_name = encoded_metric_name[:isthere].strip(" ")
                except ValueError as err:
                    raise ValueError(str(err))
            else:
                metric_tags = {}
                metric_name = encoded_metric_name.strip(" ")
        else:
            metric_name, metric_tags = self.metric_tags[encoded_metric_name]
        return metric_name, metric_tags

    def _get_tags(self, key):
        """
        This fnction will get tags of a metric
        :param key: metric key
        :returns: isthere: length of metric name
                  tags: tags of the metric
        """
        if key not in self.metric_tags.keys():
            metric_name, metric_tags = self.decode_metric_name(key)
            self.metric_tags[key] = (metric_name, metric_tags)
        else:
            metric_name, metric_tags = self.metric_tags[key]
        return metric_name, metric_tags

    def _collect_data_points(self, registry, timestamp=None):
        """
        will collect all metrics from registry and convert them to DataPoints
        :param registry: pyformance Registry containing all metrics
        :param timestamp: timestamp of data point belongs to
        :return: list of DataPoints
        """
        timestamp = timestamp or int(round(self.clock.time()))
        metrics = registry.dump_metrics()
        dps = []
        for key in metrics.keys():
            metric_name, metric_tags = self._get_tags(key)
            if self.tags is not None and self.tags != {}:
                metric_tags.update(self.tags)
            for value_key in metrics[key].keys():
                dps.append(DataPoint(metric="{0}{1}.{2}".format(self.prefix, metric_name, value_key),
                                     tags=metric_tags,
                                     timestamp=timestamp,
                                     value=metrics[key][value_key]))
        return dps
