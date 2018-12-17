# Python client for Apptuit.AI

[![Build Status](https://www.travis-ci.org/ApptuitAI/apptuit-py.svg?branch=master)](https://www.travis-ci.org/ApptuitAI/apptuit-py)
[![codecov](https://codecov.io/gh/ApptuitAI/apptuit-py/branch/master/graph/badge.svg)](https://codecov.io/gh/ApptuitAI/apptuit-py)
[![PyPI](https://img.shields.io/pypi/v/apptuit.svg)](https://pypi.org/project/apptuit/)

## Installation

```
pip install apptuit --upgrade
```

## Dependencies

Supported Python versions: 2.7.x, 3.4, 3.5, 3.6, 3.7

**Requirements** (installed automatically if you use `pip`): pandas, numpy, requests, pyformance

## Usage

### Contents
 - [Configuration](#configuration)
 - [Sending Data](#sending-data)
   * [Sending Data using ApptuitReporter](#sending-the-data-using-apptuitreporter)
   * [Sending Data using `send()` API](#sending-data-using-send-api)
 - [Querying for Data](#querying-for-data)
 
### Configuration

Apptuit package supports 2 environmental variables `APPTUIT_API_TOKEN` 
and `APPTUIT_PY_TAGS`:
* `APPTUIT_API_TOKEN`: If this environmental variable is set then you don't have 
to pass token parameter to `Apptuit()` and `ApptuitReporter()`. This will work as
a secondary token, if you pass the token to `Apptuit()` and `ApptuitReporter()` 
then that token will take priority.
* `APPTUIT_PY_TAGS`: If this environmental variable is set then these tags will 
act as global tags, and these tags will be sent in all send api calls. The tags
have to be specified in key value pair as follows:
    ```
    APPTUIT_PY_TAGS: tag_key1: tag_val1, tag_key2: tag_val2 ,..., tag_keyN: tag_valN
    ```
    If tag key in environmental variable matches tag key to `DataPoint` then 
    `DataPoint` tags take priority.

### Sending data

There are two ways of sending the data to Apptuit. First is to use the `ApptuitReporter`
class which provides high level abstraction for accumulating the data in various metrics
such as counters, timers, gauge etc. and sending them to Apptuit. The second options is to
use the `send()` method of the Apptuit client. We will show how to use both of the options below.


#### Sending the data using ApptuitReporter

You can use apptuit's pyformance reporter to report the data.
`ApptuitReporter`. [Pyformance](https://github.com/omergertel/pyformance/) is a Python implementation of
Coda Hale's Yammer metrics. It provides high level abstractions for various metrics such as
meter, counter, gauge etc. and seamlessly sends the data to the Apptuit service. For learning about
the various metrics we refer you to the [Pyformance documentation](https://github.com/omergertel/pyformance/blob/master/README.md).

**Getting started with Apptuit pyformance reporter**

```python
import socket
from pyformance import MetricsRegistry
from apptuit import timeseries
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

Few things worth pointing out in the above example:
- `reporting_interval` parameter of `ApptuitReporter` is the interval in seconds at which you wish
to report your data.
- `tags` parameter of `ApptuitReporter` specifies the global tags for this reporter.
Any metric reported by this reporter will have these set of tags added to them.
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

**Tags/Metadata**

When creating the ApptuitReporter, you can provide a set of global tags which will be part of all the metrics
reported by that reporter. However, in order to provide tags specific to each metric you need to provide them when
registering the metric with the registry. For example:

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

#### Sending data using send() API

Apart from using the Pyformance reporter, you can also use the low level `send()` API from the apptuit
client to directly send the data.

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
