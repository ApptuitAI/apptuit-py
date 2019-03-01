"""
Peocess Metrics Collection
"""
import gc
import os
import resource
import threading

from apptuit.apptuit_client import TimeSeriesName

RESOURCE_STRUCT_RUSAGE = ["ru_utime", "ru_stime",
                          "ru_maxrss", "ru_ixrss",
                          "ru_idrss", "ru_isrss",
                          "ru_minflt", "ru_majflt",
                          "ru_nswap", "ru_inblock",
                          "ru_oublock", "ru_msgsnd",
                          "ru_msgrcv", "ru_nsignals",
                          "ru_nvcsw", "ru_nivcsw"
                          ]


class ProcessMetrics(object):

    def __init__(self, registry):
        self.pid = os.getpid()
        self.registry = registry
        self.resource_metric_names = self._get_resource_metic_names()
        self.thread_metrics_names = self._get_thread_metic_names()
        self.gc_metric_names = self._get_gc_metric_names()
        self.previous_resource_metrics = [0] * len(self.resource_metric_names)
        self.previous_gc_metrics = [0] * len(self.gc_metric_names)

    def collect_process_metrics(self):
        """
        To collect all the process metrics.
        """
        rm = resource.getrusage(resource.RUSAGE_SELF)
        resource_metrics = {}
        for res_name in RESOURCE_STRUCT_RUSAGE:
            resource_metrics[res_name] = getattr(rm, res_name)
        for res_name in RESOURCE_STRUCT_RUSAGE[2:6]:
            resource_metrics[res_name] = resource_metrics[res_name] * 1024
        resource_metrics = [cur_val - pre_val
                            for cur_val, pre_val in
                            zip([resource_metrics[key]
                                 for key in resource_metrics], self.previous_resource_metrics)]
        self._collect_counter_from_list(self.resource_metric_names, resource_metrics)
        th_values = threading.enumerate()
        thread_metrics = [
            [t.daemon is True for t in th_values].count(True),
            [t.daemon is False for t in th_values].count(True),
            [isinstance(t, threading._DummyThread) for t in th_values].count(True)
        ]
        self._collect_gauge_from_list(self.thread_metrics_names, thread_metrics)
        if gc.isenabled():
            collection = list(gc.get_count())
            threshold = list(gc.get_threshold())
            gc_metrics = collection + threshold
            gc_metrics = [cur_val - pre_val
                          for cur_val, pre_val in zip(gc_metrics, self.previous_gc_metrics)]
            self._collect_counter_from_list(self.gc_metric_names, gc_metrics)
            self.previous_gc_metrics = gc_metrics
        self.previous_resource_metrics = resource_metrics

    def _get_gc_metric_names(self):
        """
        To get a list of gc metric names.
        :return: a list of gc metric names.
        """
        gc_metric_names = [
            TimeSeriesName.encode_metric("python.gc.collection",
                                         {"type": "collection_0", "worker_id": self.pid}),
            TimeSeriesName.encode_metric("python.gc.collection",
                                         {"type": "collection_1", "worker_id": self.pid}),
            TimeSeriesName.encode_metric("python.gc.collection",
                                         {"type": "collection_2", "worker_id": self.pid}),
            TimeSeriesName.encode_metric("python.gc.threshold",
                                         {"type": "threshold_0", "worker_id": self.pid}),
            TimeSeriesName.encode_metric("python.gc.threshold",
                                         {"type": "threshold_1", "worker_id": self.pid}),
            TimeSeriesName.encode_metric("python.gc.threshold",
                                         {"type": "threshold_2", "worker_id": self.pid})
        ]
        return gc_metric_names

    def _get_thread_metic_names(self):
        """
        To get a list of thread metric names.
        :return: a list of thread metric names.
        """
        thread_metric_names = [
            TimeSeriesName.encode_metric("python.thread",
                                         {"type": "demon", "worker_id": self.pid}),
            TimeSeriesName.encode_metric("python.thread",
                                         {"type": "alive", "worker_id": self.pid}),
            TimeSeriesName.encode_metric("python.thread",
                                         {"type": "dummy", "worker_id": self.pid}),
        ]
        return thread_metric_names

    def _get_resource_metic_names(self):
        """
        To get a list of resource metric names.
        :return: a list of resource metric names.
        """
        resource_metric_names = [
            TimeSeriesName.encode_metric("python.cpu.time.used.seconds",
                                         {"type": "user", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.cpu.time.used.seconds",
                                         {"type": "system", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.memory.usage.bytes",
                                         {"type": "main", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.memory.usage.bytes",
                                         {"type": "shared", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.memory.usage.bytes",
                                         {"type": "unshared", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.memory.usage.bytes",
                                         {"type": "unshared_stack_size",
                                          "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.page.faults",
                                         {"type": "major", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.page.faults",
                                         {"type": "minor", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.process.swaps",
                                         {"worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.block.operations",
                                         {"type": "input", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.block.operations",
                                         {"type": "output", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.ipc.messages",
                                         {"type": "sent", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.ipc.messages",
                                         {"type": "received", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.system.signals",
                                         {"worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.context.switches",
                                         {"type": "voluntary", "worker_id": self.pid, }),
            TimeSeriesName.encode_metric("python.context.switches",
                                         {"type": "involuntary", "worker_id": self.pid, }),
        ]
        return resource_metric_names

    def _collect_counter_from_list(self, metric_names, metric_values):
        """
        To increment list of counters `metric_names` with values `metric_values`.
        :param metric_names: A list of counter names.
        :param metric_values: A list of corresponding value to increment.
        """
        for ind, metric_value in enumerate(metric_values):
            metric_counter = self.registry.counter(metric_names[ind])
            metric_counter.inc(metric_value)

    def _collect_gauge_from_list(self, metric_names, metric_values):
        """
        To increment list of gauge `metric_names` with values `metric_values`.
        :param metric_names: A list of gauge names.
        :param metric_values: A list of corresponding value to set.
        """
        for ind, metric in enumerate(metric_values):
            metric_counter = self.registry.gauge(metric_names[ind])
            metric_counter.set_value(metric)
