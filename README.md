Python client for Apptuit

[![Build Status](https://www.travis-ci.org/ApptuitAI/apptuit-py.svg?branch=master)](https://www.travis-ci.org/ApptuitAI/apptuit-py)

### Usage -

#### Querying for data

```python
In [1]: from apptuit import Apptuit

In [2]: import time

In [3]: token = 'my_token'

In [4]: apptuit = Apptuit(token=token)

In [5]: start_time = int(time.time()) - 3600

In [6]: query_res = apptuit.query("fetch('proc.cpu.percent').downsample('1m', 'avg')", start=start_time)

In [7]: df = query_res[0].to_df()

In [8]: type(df)
Out[8]: pandas.core.frame.DataFrame

In [9]: df.shape
Out[9]: (116, 89)

# Another way of creating the DF is accessing by the metric name in the query
In [7]: another_df = query_res['proc.cpu.percent'].to_df()
```

#### Sending data

```python
In [1]: from apptuit import Apptuit, DataPoint

In [2]: import time

In [3]: import random

In [4]: token = "mytoken"

In [5]: client = Apptuit(token=token, host="http://localhost", port=4242)

In [6]: metric = "proc.cpu.percent"

In [7]: tags = {"host": "localhost", "ip": "127.0.0.1"}

In [8]: curtime = int(time.time())

In [9]: dps = []

In [10]: for i in range(10000):
    ...:     dps.append(DataPoint(metric, tags, curtime + i * 60, random.random()))
    ...:

In [11]: dps[0]
Out[11]: proc.cpu.percent{ip:127.0.0.1, host:localhost}

In [12]: client.send(dps)

In [13]: dps = []

```

