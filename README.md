# Python client for Apptuit.AI

[![Build Status](https://www.travis-ci.org/ApptuitAI/apptuit-py.svg?branch=master)](https://www.travis-ci.org/ApptuitAI/apptuit-py)
[![codecov](https://codecov.io/gh/ApptuitAI/apptuit-py/branch/master/graph/badge.svg)](https://codecov.io/gh/ApptuitAI/apptuit-py)
[![PyPI](https://img.shields.io/pypi/v/apptuit.svg)](https://pypi.org/project/apptuit/)
[![Pyversions](https://img.shields.io/pypi/pyversions/apptuit.svg?style=flat)](https://pypi.org/project/apptuit/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)



## Installation

```
pip install apptuit --upgrade
```

## Dependencies

**Requirements**
  - `requests`, `pyformance` - installed automatically if you use `pip` to install apptuit
  - `pandas` - not installed by default, you should install it manually if you intend to use the `query` API and
  create dataframes using the `to_df()` method (see [Querying for Data](#querying-for-data))

## Usage

### Contents
 - [Introduction](#introduction)
   * [Working with Apptuit Client](#working-with-apptuit-client)
   * [Working with Apptuit Pyformance Reporter](#working-with-apptuit-pyformance-reporter)
   * [Configuration](#configuration)
 - [Sending Data](#sending-data)
   * [Sending data using Apptuit pyformance reporter](#sending-data-using-apptuit-pyformance-reporter)
     * [Error Handling in ApptuitReporter](#error-handling-in-apptuitreporter)
     * [Sending Tags/Metadata](#tagsmetadata)
     * [About Host tag](#about-host-tag)
     * [Restrictions on Tags](#restrictions-on-tags-and-metric-names)
     * [Meta Metrics](#meta-metrics)
     * [Python Process Metrics](#python-process-metrics)
 - [Sending Data using `send()` API](#sending-data-using-send-api)
 - [Sending Data using `send_timeseries()` API](#sending-data-using-send_timeseries-api)
 - [Querying for Data](#querying-for-data)

### Introduction
This package provides functionality to send timeseries data to Apptuit and also to query it.
There are two main components 
- The Apptuit client - provides core functionality to query and send data
- Apptuit pyformance reporter - provides a high level abstraction on top of the client
to make it easy for you to report metrics from your applications to Apptuit.
It is based on Coda Hale's metrics design and provides primitives like
`meter`, `gauge`, `counter` to accumulate and report data.
It uses [Pyformance](https://github.com/omergertel/pyformance/) underneath.

#### Working with Apptuit Client:
The Apptuit client object can be created as simply as the following line:
```python
from apptuit import Apptuit
client = Apptuit(token=my_apptuit_token,
                 global_tags={"service": "order-service"},
                 sanitize_mode="prometheus")
```
- `token`: should be your apptuit token
- `global_tags`: should be the set of default tags you want to apply on all your data. It is an optional parameter
- `sanitize_mode`: Is a string value which specifies the sanitization mode to be used
for metric names and tag keys. 
You can set `sanitize_mode` to three values:
    - `None`: disables sanitization.
    - `apptuit`: set the sanitize mode to apptuit, which will replace
    all the invalid characters with `_`. Valid characters in this mode are all
    ASCII letters, digits, `/`, `-`, `.`, `_` and Unicode letters.
    Anyhing else is invalid character.
    - `prometheus`: set the sanitize mode to prometheus, which will replace
    all the invalid characters with `_`. Valid characters in this mode are ASCII letters, digits
    and `_`, anything else is considered invalid.


Apart from these, the Apptuit constructor takes a couple of more optional parameters explained below:

- `api_endpoint`: This should be the http endpoint for calling Apptuit apis. Normally you don't need to specify this and the default value is set to `https://api.apptuit.ai`.
- `ignore_environ_tags`: This is False by default. It tells the client whether to look up for
the global tags in environment variables or not. Global tags are tags which are applied to all the
datapoints sent through the client. We will have more to say on this in the configuration section.

The client provides two methods, `query` and `send`, which are described in the
[Querying for Data](#querying-for-data) and
[Sending data using send()](#sending-data-using-send-api) sections respectively.

#### Working with Apptuit Pyformance Reporter
The apptuit pyformance reporter is an abstraction based on Code Hale's metrics. It provides
high level primitives to accumulate data in the form of metrics such as `meter`, `timer`,
`gauge` etc. and send to Apptuit. These things are described in more
detail in the [reporter section](#sending-data-using-apptuit-pyformance-reporter),
here we will see how to create a reporter and various parameters it supports.
```python
from apptuit.pyformance import ApptuitReporter
from pyformance import MetricsRegistry

reporter_tags = {"service": "order-service"}
registry = MetricsRegistry()
reporter = ApptuitReporter(token="my_apptuit_token",
                           registry=registry,
                           reporting_interval=60,
                           tags=reporter_tags,
                           collect_process_metrics=True,
                           sanitize_mode="prometheus")

```
Here:
- `token`: Is your Apptuit token
- `registry`: Is an instance of MetricsRegistry (explained more in
[reporter section](#sending-data-using-apptuit-pyformance-reporter))
- `reporting_interval`: Number of seconds to wait before reporing again
- `tags`: A dictionary of tag keys and values.
These tags apply to all the metrics reported through this reporter.
- `collect_process_metrics`: Is a boolean value which will enable or disable collection 
of various metrics related to the Python process (CPU, memory, GC, and threads). By default
it is disabled, set this parameter to `True` to enable it.
- `sanitize_mode`: This is same as the `sanitize_mode` parameter for the
client (see above in client usage example).


#### Configuration
As we saw above, we need to pass the token and global tags as parameter to the 
Apptuit client when instantiating it. Alternatively we can set these as
environment variables, so that we don't need to hard-code them in our code.
These environment variables are described below.

* `APPTUIT_API_TOKEN`: If the Apptuit client and the ApptuitReporter are not passed a token parameter they look for the token in this variable. If this variable is also not set, the client will raise
`ApptuitException` to indicate about the missing token
* `APPTUIT_TAGS`: This is an alternative for the `global_tags` parameter for the Apptuit client. If the Apptuit client does not receive a value for `global_tags` parameter it checks this environment variable. Both the `global_tags` parameter
and `APPTUIT_TAGS` environment variable are strictly optional. If present, the Apptuit client adds those tags to every
point it is sending.

The format of the value of this variable is as follows:

```sh
export APPTUIT_TAGS="tag_key1: tag_val1, tag_key2: tag_val2, tag_key3: tag_val3"
```
The spaces after the comma and colon are optional.

The `APPTUIT_TAGS` variable is also read by the `ApptuitReporter`, which combines them with its reporter tags.
In case of a conflict of same tag keys in both sets of tags, the reporter tag take preference.

**Note**: Support for these variable was added in the version `1.0.0` of apptuit-py and is not available
in any of the earlier released versions.

### Sending data

There are two ways of sending the data to Apptuit. First is to use the `ApptuitReporter`, and
the second options is to use the `send()` method of the Apptuit client.
We will show how to use both of the options below.

### Sending data using Apptuit pyformance reporter

```python
import socket
from pyformance import MetricsRegistry
from apptuit.pyformance.apptuit_reporter import ApptuitReporter

class OrderService:
    def __init__(self, apptuit_token):
        self.registry = MetricsRegistry()
        self.init_reporter(apptuit_token, self.registry)

    def init_reporter(self, token, registry):
        hostname = socket.gethostname()
        global_tags = {"host": hostname, "env": "dev", "service": "order-service"}
        self.reporter = ApptuitReporter(registry=registry,
                                    reporting_interval=60, # data reported every 1 minute
                                    token=token,
                                    tags=global_tags,
                                    retry=2 #this will retry in case of 500 response or connection errors occur.
                                    )
        # reporter.start() will start reporting the data asynchronously based on the reporting_interval set.
        self.reporter.start()

    def handle_order(self, order):
        order_counter = self.registry.counter("order_count")
        # order handling related code
        order_counter.inc()

    def shutdown(self):
        # you can stop the reporter when you no longer wish to send data or when shutting down
        self.reporter.stop()

```

One thing worth pointing out in the above example:

- In `handle_order` we create a new counter `order_counter` with the metric name `order_count`. The first
time this method is called a new counter object will be created and registered with the registry. For
subsequent calls, that counter will get reused since internally the registry will already have a
counter with that name.

####

**MetricsRegistry**

MetricsRegistry is the container for all the metrics in our application. We can use it to register and create
various kinds of metrics (meter, gauge, counter etc.). For example:

```python
from pyformance import MetricsRegistry

registry = MetricsRegistry()
counter = registry.counter("order_count")
meter = registry.meter("order_requests_rate")
timer = registry.timer("order_requests_processing_time")
```

Now, let's take a look at the different types of metrics and how to use them.

**Meter**

A meter measures the the rate of events, such as requests per second. Meter maintains the mean rate, and
1-, 5-, 15- minute moving averages.

```python
from pyformance import MetricsRegistry

registry = MetricsRegistry()
metric_name = "order_requests_rate"
requests_meter = registry.meter(metric_name)

def handle_request(request):
    requests_meter.mark()
    # handle request

```

**Gauge**

A gauge is an instantaneous measurement of a value. For example, number of pending jobs in a queue.

```python
from queue import Queue
from pyformance import MetricsRegistry
from pyformance.meters.gauge import CallbackGauge

class QueueManager:

    def __init__(self, registry, name):
        self.q = Queue()
        jobs_metric = registry.add(name, CallbackGauge(self.get_queue_size))
    
    def get_queue_size(self):
        return self.q.size()
```

The reporter will call the `get_queue_size` function at its scheduled frequency and report
the size of the queue.

**Counter**

A counter can be used to simply count some data. It provides two methods `inc()` to increment
its value and `dec()` to decrement it.

```python

from pyformance import MetricsRegistry

registry = MetricsRegistry()
jobs_counter = registry.counter('pending_jobs')

def add_job(self, job):
    jobs_counter.inc(1)
    self.q.put(job)

def take_job(self):
    jobs_counter.dec(1)
    self.q.get()
```

**Timer**

A timer aggregates timing durations and provides duration statistics, as well as throughput statistics.

```python
from pyformance import MetricsRegistry

registry = MetricsRegistry()
timer = registry.timer("response_time")

def handle_request(request):
    with timer.time():
        return "OK"

```
The above example will use the timer to report the time taken to serve each request.

**Histogram**

A histogram measures the statistical distribution of values in a stream of data. It provides aggregate data
such as the min, max, mean, sum, and count.

```python

from pyformance import MetricsRegistry

registry = MetricsRegistry()

response_sizes = registry.histogram('response_size')

def handle_request(request):
    response = do_query(request) # process the query
    response_sizes.add(response.size())

```
#### Error Handling in ApptuitReporter
The ApptuitReporter sends data asynchronously (unless we are explicitly using it in synchronous mode
by not calling the `start()` method). In asynchronous
mode it is very difficult to know if the reporter is working properly or not. To make this easier the
`ApptuitReporter` takes an `error_handler` argument. `error_handler` is expected to be a function reference
which takes 4 arguments. The signature of the function and the arguments are explained below:

```python
  def error_handler(status_code, successful_points_count, failed_points_count, errors):
    pass
```
- `status_code`: The HTTP status code of the POST API call to Apptuit
- `successful_points_count`: Number of points successfully processed
- `failed_points_count`: Number of points which could not be processed due to errors
- `errors`: List of error messages describing the reason of failure of each of the failed points

By default, the `ApptuitReporter` registers a `default_error_handler`, which writes the errors to `stderr`.
To override that you can pass your own error handler implementation, or if you don't wish to do anything for errors
you can pass `None` for the `error_handler` argument.

**Reporter with default error handler**
```python
import logging
#reporter with default error handler (writes to stderr)
reporter = ApptuitReporter(token=my_apptuit_token,
                           registry=registry,
                           reporting_interval=60,
                           tags=reporter_tags)
```
**Reporter with No error handler**
```python
reporter_with_no_error_handler = ApptuitReporter(
                            token=my_apptuit_token,
                            registry=registry,
                            reporting_interval=60,
                            tags=reporter_tags,
                            error_handler=None
                            )
```

The error handler function by definition takes only four arguments.
If you wish to pass extra arguments to the error handler you can use
closures or partial functions to get around the limitation.

**Passing extra argument using Partial**

```python
import logging
from functools import partial

def custom_error_handler(logger, status_code, successful, failed, errors):
    logger.error("ApptuitReporter failed to send %d points, due to errors: %s" % (failed, str(errors)))

logger = logging.getLogger("logger key")
apptuit_custom_error_handler = partial(custom_error_handler, logger)
reporter = ApptuitReporter(
            token=my_apptuit_token,
            registry=registry,
            reporting_interval=60,
            tags=reporter_tags,
            error_handler=apptuit_custom_error_handler
            )
```
**Passing extra argument using closure**
```python
...
import logging
from apptuit import ApptuitSendException
from apptuit.pyformance.apptuit_reporter import ApptuitReporter
...

class OrderService:
    def __init__(self, apptuit_token):
        ...
        self.logger = logging.getLogger("OrderService")
        ...

    def init_reporter(self, token, registry):
        ...
        def apptuit_error_handler(status_code, successful, failed, errors):
            logger = self.logger
            logger.error(str(ApptuitSendException(
                status_code, successful, failed, errors
            )))
            
        self.reporter = ApptuitReporter(...,
                                    error_handler=apptuit_error_handler)
        ...

```

#### Tags/Metadata

When creating the ApptuitReporter, you can provide a set of tags (referred as reporter tags from now on)
which will be part of all the metrics reported by that reporter. However, in order to provide tags
specific to each metric you need to provide them when registering the metric with the registry. For example:

```python
from apptuit import timeseries
from pyformance import MetricsRegistry

registry = MetricsRegistry()
metric_name = "node_cpu"
tags = {"type": "idle", "host": "node-foo", "service": "order-service"}
metric = timeseries.encode_metric(metric_name, tags)
meter = registry.meter(metric)
```
Here we provided the metric specific tags by calling `timeseries.encode_metric` and
providing the metric name and the tags as parameters. When registering the metric we provide this
encoded name to the registry instead of the plain metric name.

To decode an encoded metric name use the `decode_metric()` function from `timeseries` module.
```python

from apptuit import timeseries

encoded_metric = timeseries.encode_metric("node.cpu", {"type": "idle"})
metric_name, tags = timeseries.decode_metric(encoded_metric)
```

A *recommended practise* is to maintain a local cache of the created metrics and reuse them, rather than
creating them every time:

```python
import socket
import time
from apptuit import timeseries
from apptuit.pyformance import ApptuitReporter
from pyformance import MetricsRegistry

class OrderService:

    def __init__(self, apptuit_token):
        self.registry = MetricsRegistry()
        self.init_reporter(apptuit_token, self.registry)
        self.order_counters = {}

    def init_reporter(self, token, registry):
        hostname = socket.gethostname()
        global_tags = {"host": hostname, "env": "dev", "service": "order-service"}
        self.reporter = ApptuitReporter(registry=registry,
                                    reporting_interval=60, # data reported every 1 minute
                                    token=token,
                                    tags=global_tags)
        # reporter.start() will start reporting the data asynchronously based on the reporting_interval set.
        self.reporter.start()

    def get_order_counter(self, city_code):
        # We have counters for every city code
        if city_code not in self.order_counters:
            tags = {"city-code": city_code}
            metric = timeseries.encode_metric("order_count", tags=tags)
            self.order_counters[city_code] = self.registry.counter(metric)
        return self.order_counters[city_code]

    def handle_order(self, order):
        order_counter = self.get_order_counter(order.city_code)
        order_counter.inc()
        self.process_order(order)

    def shutdown(self):
        # you can stop the reporter when you no longer wish to send data or when shutting down
        self.reporter.stop()

    def process_order(self, order):
        time.sleep(5)

```

Here we have a method `get_order_counter` which takes the `city_code` as a parameter. There
is a local cache of counters keyed by the encoded metric names. This avoids the unnecessary overhead
of encoding the metric name and tags every time, if we already have created a counter for that city.
It also ensures that we will report separate time-series for order-counts of different city codes.

#### About Host Tag
The reporter will add a `host` tag key with host name as its value (obtained by calling `socket.gethostname()`).
This is helpful in order to group the metrics by host if the reporter is being run on multiple servers. The value
of the `host` tag key can be overridden by passing our own `host` tag in the `tags` parameter to the reporter or
by setting a `host` tag in the global environment variable for tags

If we don't wish for the `host` tag to be set by default we can disable it by setting the
`disable_host_tag` parameter of the reporter to `True`. Alternatively we can set the environment
variable `APPTUIT_DISABLE_HOST_TAG` to `True` to disable it.

#### Restrictions on Tags and Metric names
- **Allowed characters in tag keys and metric names** - Tag keys and metric names can have any unicode 
etters (as defined by unicode specification) and the following special characters:  `.`, `-`, `_`, `/`.
However, if we are looking to follow Prometheus compliant naming
([see specification])(https://prometheus.io/docs/concepts/data_model/#metric-names-and-labels)
we should restrict them to ASCII letters, digits and  underscores only and it must match the
regex `[a-zA-Z_][a-zA-Z0-9_]*`. No such restriction is applicable on tag values.
- **Maximum number of tags** - Apptuit currently allows upto 25 tag key-value pairs per datapoint

#### Meta Metrics
The `ApptuitReporter` also reports a set of meta metrics which can be a useful indicator if the reporter is 
working as expected or not, as well as to get a sense of how many points are being sent and the latency of
the Apptuit API. These meta metrics are described below.

- `apptuit_reporter_send_total` - Total number of points sent
- `apptuit_reporter_send_successful` - Number of points which were succssfully processed
- `apptuit_reporter_send_failed` - Number of points which failed
- `apptuit_reporter_send_time` - Timing stats of of the send API

#### Python Process Metrics
The `ApptutiReporter` can also be configured to report various metrics of
the Python process it is running in. By default it is disabled but we can enable it by
passing setting the parameter `collect_process_metrics` to `True` when creating the
reporter object. The reporter will collect metrics related to the system resource usage
by the process (cpu, memory, IPC etc.) as well as metrics related to garbage collection
and threads. The complete list of all the metrics collected is provided below:
- `python_cpu_time_used_seconds` - Total time spent by the process in user mode and system mode.
- `python_memory_usage_bytes` - Total amount of memory used by the process.
- `python_page_faults` - Total number of page faults received by the process.
- *`python_process_swaps` - Total number of times the process was swapped-out of the main memory.
- `python_block_operations` - Total number of block input and output operations.
- `python_ipc_messages` - Total number of inter-process messages sent and received by the process. 
- *`python_system_signals` - Total number of signals received by the process.
- `python_context_switches` - Total number of context switches of the process.
- `python_thread` - Count of active, demon and dummy threads.
- `python_gc_collection` - Count of objects collected in gc for each generation. 
- `python_gc_threshold` - Value of garbage collector threshold for each generation.

**Note** - Metrics marked with `*` are zero on Linux because it does not support them

#### Global tags, reporter tags and metric tags

When using the reporter we have three sets of tags, it's better to clarify a few things about them.

- `ApptuitReporter` takes a set of tags as parameter. It adds these tags to all the metrics it is reporting.
- If the environment variable `APPTUIT_TAGS` is set, the reporter takes those into account as well, however
the tags passed to it take preference in case of a conflict because of common tag keys.
- Each metric being reported by the reporter might also have some tags attached, in case of a conflict
because of common tag keys, the metric tags take preference over reporter or global tags.

#### Sending data using send() API

Apart from using the Pyformance reporter, you can also use the low level `send()` API from the apptuit
client to directly send the data. If you want tags while sending you can use the global_tags
parameter of Apptuit class. If global_tags are set then environmental tags will not be used.

```python
from apptuit import Apptuit, DataPoint
import time
import random
import socket

token = "mytoken"
client = Apptuit(token=token)
metrics = ["proc.cpu.percent", "node.memory.bytes", "network.send.bytes", "network.receive.bytes", "node.load.avg"]
tags = {"host": socket.gethostname()}
curtime = int(time.time())
dps = []
while True:
    curtime = int(time.time())
    for metric in metrics:
        dps.append(DataPoint(metric, tags, curtime, random.random()))
    if len(dps) == 100:
        client.send(dps, 
                retry_count=3 #this will retry in case of 500 response or connection errors occur.
            )
        dps = []
    time.sleep(60)
```

#### Sending data using send_timeseries() API
The `send` API works with a list of DataPoint objects. Creating each DataPoint object involves validating the metric name and
the tags. If we are creating thousands of DataPoint objects with the metric name and tags, it can quickly get very expensive.
In order to avoid that overhead, there is an alternative `send_timeseries` API as well, which accepts a list of `TimeSeries`
objects. This is much more convenient as we need to create a `TimeSeries` object with a metric name and tags. Thereafter
we can add points to that timeseries object by calling its `add_point()` method. This avoids creation of DataPoint objects
and the overhead of the tag validation.

Following is an example from a scraper we run internally. We call an HTTP API, get a JSON response and send it to us in the
form of timeseries. In order to avoid too many API calls to Apptuit we call `send_timeseries` whenever we have accumulated
50000 or more points. Once we make a `send_timeseries` call we reset the `series_list` object to contain just the latest
`TimeSeries` object (all the earlier series would have been sent to Apptuit).

```python
from apptuit import Apptuit, TimeSeries

series_list = []
points_count = 0
token = "mytoken"
client = Apptuit(token=token)
response_data = make_request()
for result in response_data["results"]:
    metric_name = result["metric"]
    tags = result["tags"]
    series = TimeSeries(metric_name, tags)
    series_list.append(series)
    for timestamp, value in result["values"]:
        series.add_point(timestamp, value)
        points_count += 1
        if points_count >= 50000:
            client.send_timeseries(series_list)
            points_count = 0
            series_list = [TimeSeries(metric_name, tags)]
if points_count > 0:
    client.send_timeseries(series_list)
```

### Querying for data

```python

from apptuit import Apptuit
import time
token = 'my_token' # replace with your Apptuit token
apptuit = Apptuit(token=token)
start_time = int(time.time()) - 3600 # let's query for data going back 1 hour from now
query_res = apptuit.query("fetch('proc.cpu.percent').downsample('1m', 'avg')", start=start_time
                            retry_count=3 #this will retry in case of 500 response or connection errors occur.
                        )
# we can create a Pandas dataframe from the result object by calling to_df()
df = query_res[0].to_df()
# Another way of creating the DF is accessing by the metric name in the query
another_df = query_res['proc.cpu.percent'].to_df()
```
It should be noted that using the `to_df()` method requires that you have `pandas` installed.
We don't install `pandas` by default as part of the requirements because not every user of the library
would want to query or create dataframes (many users just use the `send` API or the reporter functionality)
