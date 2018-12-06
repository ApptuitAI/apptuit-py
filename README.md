# Python client for Apptuit.AI

[![Build Status](https://www.travis-ci.org/ApptuitAI/apptuit-py.svg?branch=master)](https://www.travis-ci.org/ApptuitAI/apptuit-py)
[![codecov](https://codecov.io/gh/ApptuitAI/apptuit-py/branch/master/graph/badge.svg)](https://codecov.io/gh/ApptuitAI/apptuit-py)
![PyPI](https://img.shields.io/pypi/v/apptuit.svg)

## Installation

```
pip install apptuit
```

## Dependencies

Supported Python versions: 2.7.x, 3.4, 3.5, 3.6, 3.7

Requirements:
- pandas
- numpy
- requests

## Usage

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

### Sending data

```python
from apptuit import Apptuit, DataPoint
import time
import random
token = "mytoken"
client = Apptuit(token=token)
metrics = ["proc.cpu.percent", "node.memory.bytes", "network.send.bytes", "network.receive.bytes", "node.load.avg"]
tags = {"host": "localhost", "ip": "127.0.0.1"}
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

### Reporter

ApptuitReporter is an API which sends the data to Apptuit servers, you can send report data in two ways.
Reporting data:
- `reporter.start()`: This will report asynchronously on a different thread. You can stop that thread by using `reporter.stop()`.  
- `reporter.report_now()`: This will report synchronously on same thread.

```python

#imports
from pyformance import MetricsRegistry
from apptuit.pyformance.apptuit_reporter import ApptuitReporter

#requirements
registry = MetricsRegistry()
token = "token"
tags = {"host": "localhost", "region": "us-east-1", "service": "web-server"}

#creating a reporter
reporter = ApptuitReporter(registry=registry, #registry with metrics 
                            reporting_interval=1, #interval between successive reports
                            token=token,
                            prefix="apr.",
                            tags=tags)

#Synchronus Report, sending on same thread.
reporter.report_now()#to report manually

#Asynchronus Report, sending from other thread.
reporter.start()#starting a reaporter
```

### Various Metrics

#### Counter

```python

from pyformance import MetricsRegistry

#creating registry
registry = MetricsRegistry()

#creating a counter metric
counter = registry.counter("example_counter")

#using counter
counter.inc(2)
counter.dec(3)
```

#### Timer

```python
from time import sleep
from pyformance import MetricsRegistry

#creating registry
registry = MetricsRegistry()

#creating a timer metric
timer = registry.timer("example_counter")

#using timer
with timer.time():
    sleep(0.2)

print(timer.get_mean()) #Output: 0.20072579383850098
```

#### Histogram

```python

from pyformance import MetricsRegistry

#creating registry
registry = MetricsRegistry()

#creating a histogram metric
hist = registry.histogram("example_counter")

#using histogram
hist.add(10)
hist.add(20)
hist.add(30)
print(hist.get_mean()) #Output: 20.0
```
