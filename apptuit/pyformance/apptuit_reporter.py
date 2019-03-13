#
# Copyright 2018 Agilx, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
Apptuit Pyformance Reporter
"""
import os
import socket
import sys
import time

from pyformance import MetricsRegistry
from pyformance.reporters.reporter import Reporter

from apptuit.apptuit_client import Apptuit, DataPoint, ApptuitSendException, TimeSeriesName
from .process_metrics import ProcessMetrics
from ..utils import _get_tags_from_environment, strtobool

NUMBER_OF_TOTAL_POINTS = "apptuit.reporter.send.total"
NUMBER_OF_SUCCESSFUL_POINTS = "apptuit.reporter.send.successful"
NUMBER_OF_FAILED_POINTS = "apptuit.reporter.send.failed"
API_CALL_TIMER = "apptuit.reporter.send.time"
DISABLE_HOST_TAG = "APPTUIT_DISABLE_HOST_TAG"
BATCH_SIZE = 50000


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
                 error_handler=default_error_handler, disable_host_tag=None,
                 collect_process_metrics=False, sanitize_mode="prometheus"):
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
                number of points processed successfully, failed_points is number of failed points
                and errors is a list of error messages describing reason of each failure.
            disable_host_tag: By default a host tag will be added to all the metrics reported by
                the reporter. Set disable_host_tag to False if you wish to disable it
            collect_process_metrics: A boolean variable specifying if process metrics should be
                collected or not, if set to True then process metrics will be collected. By default,
                this will collect resource, thread, and gc metrics.
            sanitize_mode: Is a string value which will enable sanitizer, sanitizer will
                    automatically change your metric names to be compatible with apptuit
                    or prometheus. Set it to None if not needed.
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
        if disable_host_tag is None:
            disable_host_tag = os.environ.get(DISABLE_HOST_TAG, False)
            if disable_host_tag:
                disable_host_tag = strtobool(disable_host_tag)

        if not disable_host_tag:
            if self.tags:
                if self.tags.get("host") is None:
                    self.tags["host"] = socket.gethostname()
            else:
                self.tags = {"host": socket.gethostname()}
        self.prefix = prefix if prefix is not None else ""
        self.client = Apptuit(token=token, api_endpoint=api_endpoint,
                              ignore_environ_tags=True, sanitize_mode=sanitize_mode)
        self._meta_metrics_registry = MetricsRegistry()
        self.error_handler = error_handler
        self.process_metrics = None
        if collect_process_metrics:
            self.process_metrics = ProcessMetrics(self.registry)

    def _update_counter(self, key, value):
        """
        To increment the counter with `key` by `value`.
        :param key: Name of counter.
        :param value: value to increment.
        """
        self._meta_metrics_registry.counter(key).inc(value)

    def report_now(self, registry=None, timestamp=None):
        """
        Report the data
        Params:
            registry: pyformance Registry containing all metrics
            timestamp: timestamp of the data point
        """
        if self.process_metrics:
            self.process_metrics.collect_process_metrics()
        dps = self._collect_data_points(registry or self.registry, timestamp)
        meta_dps = self._collect_data_points(self._meta_metrics_registry)
        if not dps:
            return
        dps_len = len(dps)
        success_count = 0
        failed_count = 0
        errors = []
        for i in range(0, dps_len, BATCH_SIZE):
            try:
                with self._meta_metrics_registry.timer(API_CALL_TIMER).time():
                    end_index = min(dps_len, i + BATCH_SIZE)
                    self.client.send(dps[i: end_index])
                    points_sent_count = end_index - i
                    self._update_counter(NUMBER_OF_TOTAL_POINTS, points_sent_count)
                    self._update_counter(NUMBER_OF_SUCCESSFUL_POINTS, points_sent_count)
                    self._update_counter(NUMBER_OF_FAILED_POINTS, 0)
                    success_count += points_sent_count
            except ApptuitSendException as exception:
                self._update_counter(NUMBER_OF_SUCCESSFUL_POINTS, exception.success)
                self._update_counter(NUMBER_OF_FAILED_POINTS, exception.failed)
                success_count += exception.success
                failed_count += exception.failed
                errors += exception.errors
                if self.error_handler:
                    self.error_handler(
                        exception.status_code,
                        exception.success,
                        exception.failed,
                        exception.errors
                    )
        self.client.send(meta_dps)
        if failed_count != 0:
            raise ApptuitSendException("Failed to send %d out of %d points" %
                                       (failed_count, dps_len), success=success_count,
                                       failed=failed_count, errors=errors)

    @staticmethod
    def _get_tags(key):
        """
        Get tags of a metric
        Params:
            metric key
        Returns:
            metric name, dictionary of tags
        """
        metric_name, metric_tags = TimeSeriesName.decode_metric(key)
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
                data_point = DataPoint(
                    metric=self.prefix + metric_name + '.' + value_key,
                    tags=tags, timestamp=timestamp, value=metrics[key][value_key])
                dps.append(data_point)
        return dps

    def _loop(self):
        while not self._stopped.is_set():
            start = time.time()
            try:
                self.report_now(self.registry)
            except Exception:
                pass
            end = time.time()
            wait_time = max(0, self.reporting_interval-(end-start))
            time.sleep(wait_time)
