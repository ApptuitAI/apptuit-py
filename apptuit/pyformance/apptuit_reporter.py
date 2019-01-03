"""
Apptuit Pyformance Reporter
"""
import sys
from pyformance import MetricsRegistry
from pyformance.reporters.reporter import Reporter
from apptuit import Apptuit, DataPoint, timeseries, ApptuitSendException
from apptuit.utils import _get_tags_from_environment

NUMBER_OF_TOTAL_POINTS = "apptuit.reporter.send.total"
NUMBER_OF_SUCCESSFUL_POINTS = "apptuit.reporter.send.successful"
NUMBER_OF_FAILED_POINTS = "apptuit.reporter.send.failed"
API_CALL_TIMER = "apptuit.reporter.send.time"

def default_error_handler(status_code, successful, failed, errors):
    """
    This is the default error handler for the ApptuitReporter.
    It simply writes the errors to stderr.
    Parameters
    ----------
        status_code: response status_code of Apptuit.send()
        successful: number of datapoints updated successfully
        failed: number of datapoints updating failed
        errors: errors in response
    """
    msg = "%d points out of %d had errors\n" \
          "HTTP status returned from Apptuit: %d\n" \
          "Detailed error messages: %s\n" % \
          (failed, successful + failed, status_code, str(errors))
    sys.stderr.write(msg)

class ApptuitReporter(Reporter):
    """
        Pyformance based reporter for Apptuit. It provides high level
        primitives, such as meter, counter, gauge, etc., for collecting
        data and reports them asynchronously to Apptuit.
    """

    def __init__(self, registry=None, reporting_interval=10, token=None,
                 api_endpoint="https://api.apptuit.ai", prefix="", tags=None,
                 error_handler=default_error_handler):
        """
        Parameters
        ----------
            registry: An instance of MetricsRegistry from pyformance. It is
                used as a container for all the metrics. If None, a new instance will be
                created internally
            reporting_interval: Reporting interval in seconds
            token: Apptuit API token
            prefix: Optional prefix for metric names, this will be prepended to all the
                metric names
            tags: A dictionary of tag keys and values which will be included with
                all the metrics reported by this reporter
            error_handler: A function to be executed in case of errors when reporting
                the data. If not specified, the default error handler will be used which by
                default writes the errors to stderr. The expected signature of an error handler
                is: error_handler(status_code, successful_points, failed_points, errors). Here
                status_code is the HTTP status code of the failed API call, successful_points is
                number of points processed succesfully, failed_points is number of failed points
                and errors is a list of error messages describing reason of each failure.
        """
        super(ApptuitReporter, self).__init__(registry=registry,
                                              reporting_interval=reporting_interval)
        self.endpoint = api_endpoint
        self.token = token
        self.tags = tags
        environ_tags = _get_tags_from_environment()
        if environ_tags:
            if self.tags is not None:
                environ_tags.update(self.tags)
            self.tags = environ_tags
        self.prefix = prefix if prefix is not None else ""
        self.__decoded_metrics_cache = {}
        self.client = Apptuit(token, api_endpoint, ignore_environ_tags=True)
        self._meta_metrics_registry = MetricsRegistry()
        self.error_handler = error_handler

    def _update_counter(self, key, value):
        self._meta_metrics_registry.counter(key).inc(value)

    def report_now(self, registry=None, timestamp=None):
        """
        Report the data
        Params:
            registry: pyformance Registry containing all metrics
            timestamp: timestamp of the data point
        """
        dps = self._collect_data_points(registry or self.registry, timestamp)
        self._update_counter(NUMBER_OF_TOTAL_POINTS, len(dps))
        meta_dps = self._collect_data_points(self._meta_metrics_registry)
        if dps:
            try:
                with self._meta_metrics_registry.timer(API_CALL_TIMER).time():
                    self.client.send(dps + meta_dps)
                    self._update_counter(NUMBER_OF_SUCCESSFUL_POINTS, len(dps))
                    self._update_counter(NUMBER_OF_FAILED_POINTS, 0)
            except ApptuitSendException as exception:
                exception.success -= len(meta_dps)
                self._update_counter(NUMBER_OF_SUCCESSFUL_POINTS, exception.success)
                self._update_counter(NUMBER_OF_FAILED_POINTS, exception.failed)
                if self.error_handler:
                    self.error_handler(
                        exception.status_code,
                        exception.success,
                        exception.failed,
                        exception.errors
                    )
                raise exception

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
                dp = DataPoint(metric="{0}{1}.{2}".format(self.prefix, metric_name, value_key),
                               tags=tags, timestamp=timestamp, value=metrics[key][value_key])
                dps.append(dp)
        return dps
