# Python client for Apptuit.AI

[![Build Status](https://www.travis-ci.org/ApptuitAI/apptuit-py.svg?branch=master)](https://www.travis-ci.org/ApptuitAI/apptuit-py)
[![codecov](https://codecov.io/gh/ApptuitAI/apptuit-py/branch/master/graph/badge.svg)](https://codecov.io/gh/ApptuitAI/apptuit-py)
[![PyPI](https://img.shields.io/pypi/v/apptuit.svg)](https://pypi.org/project/apptuit/)
[![Pyversions](https://img.shields.io/pypi/pyversions/apptuit.svg?style=flat)](https://pypi.org/project/apptuit/)

## Installation

```
pip install apptuit --upgrade
```

## Dependencies

**Requirements** (installed automatically if you use `pip`): pandas, numpy, requests, pyformance

## Usage

### Contents
 - [Introduction](#introduction)
   * [Working with Apptuit Client](#working-with-apptuit-client)
   * [Working with Apptuit Pyformance Reporter](#working-with-apptuit-pyformance-reporter)
   * [Configuration](#configuration)
 - [Sending Data](#sending-data)
   * [Sending Data using ApptuitReporter](#sending-the-data-using-apptuitreporter)
     * [Getting started with Apptuit pyformance reporter](#getting-started-with-apptuit-pyformance-reporter)
     * [Error Handling](#error-handling)
     * [Tags/Metadata](#tagsmetadata)
     * [Meta Metrics](#meta-metrics)
 - [Sending Data using `send()` API](#sending-data-using-send-api)
 - [Querying for Data](#querying-for-data)

### Introduction
This package provides functionality to send timeseries data to Apptuit and also to query it.
There are two main components 
- The Apptuit client - provides core functionality to query and send data
- Apptuit pyformance reporter - provides a high level abstraction on top of the client
to make it easy for you to report metrics from your applications to Apptuit.
It is based on Coda Hale's metrics design and implemented using and provides primitives like
`meter`, `gauge`, `counter` to accumulate and report data.
It uses [Pyformance](https://github.com/omergertel/pyformance/) underneath.

#### Working with Apptuit Client:
The Apptuit client object can be created as simply as the following line:
```python
from apptuit import Apptuit
client = Apptuit(token=my_apptuit_token, global_tags={"service": "order-service"})
```
- `token`: should be your apptuit token
- `global_tags`: should be the set of default tags you want to apply on all your data. It is an optional parameter

Apart from these, the Apptuit constructor takes a couple of more optional parameters explained below:

- `api_endpoint`: This should be the http endpoint for calling Apptuit apis. Normally you don't need to specify this and the default value is set to `https://api.apptuit.ai`.
- `ignore_environ_tags`: This is False by default. It tells the client whether to look up for
the global tags in environment variables or not. We will have more to say on this in the configuration section.

The client provides two methods `query` and `send` which are described in the
"Querying for Data" and "Sending data using send()" sections respectively

#### Working with Apptuit Pyformance Reporter
The apptuit pyformance reporter is an abstraction based on Code Hale's metrics. It provides
high level abstractions to accumulate data in the form of metrics such as `meter`, `timer`,
`gauge` etc. and send to Apptuit. These things are described in more detail in the reporter section,
here we will see how to create a reporter and various parameter it supports.
```python
from apptuit.pyformance import ApptuitReporter
from pyformance import MetricsRegistry

reporter_tags = {"service": "order-service"}
registry = MetricsRegistry()
reporter = ApptuitReporter(token=my_apptuit_token,
                           registry=registry,
                           reporting_interval=60,
                           tags=reporter_tags)

```
Here:
`token`: Is your Apptuit token
`registry`: Is an instance of MetricsRegistry (explained more in Reporter section)
`reporting_interval`: Number of seconds to wait before reporing again
`tags`: Tags - these tags apply to all the metrics reported through this reporter.

#### Configuration
As we saw above, we need to pass the token and global tags as parameter to the 
Apptuit client when instantiating it. There is an alternative to set these as
environment variables, in which case you don't need to pass them explicitly in your code.
These variables are described below

* `APPTUIT_PY_TOKEN`: If the Apptuit client and the ApptuitReporter are not passed a token parameter they look for the token in this variable.
* `APPTUIT_PY_TAGS`: This is an alternative for the `global_tags` parameter for the Apptuit client. If the Apptuit client does not receive a value for `global_tags` parameter it checks this environment variable. Both the `global_tags` parameter
and `APPTUIT_PY_TAGS` environment variable are strictly optional. If present the Apptuit client adds those tags to every
point it is sending.

The format of the value of this variable is as follows:

```sh
export APPTUIT_PY_TAGS="tag_key1: tag_val1, tag_key2: tag_val2, tag_key3: tag_val3"
```
The spaces after the comma and colon are optional.

The `APPTUIT_PY_TAGS` variable is also read by the `ApptuitReporter`, which combines them with its reporter tags.
In case of a conflict of same tag keys in both sets of tags, the reporter tag take preference.

**Note**: Support for these variable has been added in the development version of apptuit-py and is not available
in any of the released versions.

### Sending data

There are two ways of sending the data to Apptuit. First is to use the `ApptuitReporter`, and
the second options is to use the `send()` method of the Apptuit client.
We will show how to use both of the options below.

#### Sending the data using ApptuitReporter

You can use apptuit's pyformance reporter to report the data.
`ApptuitReporter`. [Pyformance](https://github.com/omergertel/pyformance/) is a Python implementation of
Coda Hale's Yammer metrics. 

#### Getting started with Apptuit pyformance reporter

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
                                    tags=global_tags)
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

MetricsRegistry is the container for all the metrics in your application. You can use it to register and create
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
#### Error Handling
While sending data from ApptuitReporter some datapoints might have errors or server errors might occur, you can 
use the parameter error_handler to work on those errors. You cant pass any parameters to that error handler but 
can use the python feature like closure or use partial from functools package. There is a default error handler 
which will write the errors to stderr. If you dont want any error handling you can pass `error_handler=None` which 
will disable default error handler.
```python
from apptuit.pyformance import ApptuitReporter
from pyformance import MetricsRegistry
import logging
reporter_tags = {"service": "order-service"}
registry = MetricsRegistry()
my_apptuit_token = "token"
#reporter with default error handler (writes to stderr)
reporter = ApptuitReporter(token=my_apptuit_token,
                           registry=registry,
                           reporting_interval=60,
                           tags=reporter_tags)

#reporter without error handler
reporter_with_no_error_handler = ApptuitReporter(
                            token=my_apptuit_token,
                            registry=registry,
                            reporting_interval=60,
                            tags=reporter_tags,
                            error_handler=None
                            )

#reporter with custom error_handler using partial
def custom_error_handler_partial(logger, status_code, successful, failed, errors):
    logger.error(str(ApptuitSendException(
        status_code, successful, failed, errors
    )))
from functools import partial
logger = logging.getLogger("logger key")
apptuit_custom_error_handler = partial(custom_error_handler_partial,logger)

reporter_with_no_error_handler = ApptuitReporter(
                            token=my_apptuit_token,
                            registry=registry,
                            reporting_interval=60,
                            tags=reporter_tags,
                            error_handler=apptuit_custom_error_handler
                            )


#reporter with custom error_handler using closure
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
        def custom_error_handler_closure(status_code, successful, failed, errors):
            logger = self.logger
            logger.error(str(ApptuitSendException(
                status_code, successful, failed, errors
            )))
            
        self.reporter = ApptuitReporter(...,
                                    error_handler=custom_error_handler_closure)
        # reporter.start() will start reporting the data asynchronously based on the reporting_interval set.
        self.reporter.start()
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

A *good practise* is to maintain a local cache of the created metrics and reuse them, rather than
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

#### Meta Metrics
Reporter also sends a few metrics such as total data points sent, number of successful data points, 
number of failed data points, and time for sending data points. These will be send along with the metrics

```python
NUMBER_OF_TOTAL_POINTS = "apptuit.reporter.send.total"
NUMBER_OF_SUCCESSFUL_POINTS = "apptuit.reporter.send.successful"
NUMBER_OF_FAILED_POINTS = "apptuit.reporter.send.failed"
API_CALL_TIMER = "apptuit.reporter.send.time"
```

#### Global tags, reporter tags and metric tags

When using the reporter we have three sets of tags, it's better to clarify a few things about them.

- `ApptuitReporter` takes a set of tags as parameter. It adds these tags to all the metrics it is reporting.
- If the environment variable `APPTUIT_PY_TAGS` is set, the reporter takes those into account as well, however
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
        client.send(dps)
        dps = []
    time.sleep(60)
```

### Querying for data

```python

from apptuit import Apptuit
import time
token = 'my_token' # replace with your Apptuit token
apptuit = Apptuit(token=token)
start_time = int(time.time()) - 3600 # let's query for data going back 1 hour from now
query_res = apptuit.query("fetch('proc.cpu.percent').downsample('1m', 'avg')", start=start_time)
# we can create a Pandas dataframe from the result object by calling to_df()
df = query_res[0].to_df()
# Another way of creating the DF is accessing by the metric name in the query
another_df = query_res['proc.cpu.percent'].to_df()

```
