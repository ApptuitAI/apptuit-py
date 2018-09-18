# Python client for Apptuit.AI

[![Build Status](https://www.travis-ci.org/ApptuitAI/apptuit-py.svg?branch=master)](https://www.travis-ci.org/ApptuitAI/apptuit-py)

### Installation

```
pip install apptuit
```

### Dependencies

Supported Python versions: 2.7.x, 3.4, 3.5, 3.6, 3.7

Requirements:
- pandas
- numpy
- requests

### Usage

#### Querying for data

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

#### Sending data

```python
from apptuit import Apptuit, DataPoint
import time
import random
token = "mytoken"
client = Apptuit(token=token)
metric = "proc.cpu.percent"
tags = {"host": "localhost", "ip": "127.0.0.1"}
curtime = int(time.time())
dps = []
while True:
    dps.append(DataPoint(metric, tags, curtime + i * 60, random.random()))
    if len(dps) == 5000:
        client.send(dps)
        dps = []
```
