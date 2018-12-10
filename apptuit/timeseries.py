"""
    Utility functions for timeseries
"""

import json

def encode_metric(metric_name, metric_tags):
    """
    Generate an encoded metric name by combining metric_name and metric_tags
    Params:
        metric_name: name of the metric
        metric_tags: tags (expected a dictionary of tag keys vs values)
    Returns: An string encoding the metric name and the tags which can be used when
                creating metric objects, such as counters, timers etc.
    Example:
        s = reporter.encode_metric_name('node.cpu', {"type": "idle"})
        print(s) # 'node.cpu {"type": "idle"}'
    """
    if not isinstance(metric_name, str):
        raise ValueError("metric_name should be a string")
    if metric_name == "":
        raise ValueError("metric_name cannot be empty")
    if not isinstance(metric_tags, dict):
        raise ValueError("metric_tags must be a dictionary")

    encoded_metric_name = metric_name + json.dumps(metric_tags, sort_keys=True)
    return encoded_metric_name


def decode_metric(encoded_metric_name):
    """
    Decode the metric name as encoded by encode_metric_name
    Params:
        encoded_metric_name: a string encoded in a format as returned by encode_metric_name()
            example: 'metricName {"metricTagKey1":"metricValue1","metricTagKey2":"metricValue2"}'
    Returns:
        The metric name and the dictionary of tags
    """
    if encoded_metric_name is None or encoded_metric_name == "":
        raise ValueError("Invalid value for encoded_metric_name")

    metric_tags = {}
    metric_name = encoded_metric_name.strip()
    brace_index = encoded_metric_name.find('{')
    if brace_index > -1:
        try:
            metric_tags = json.loads(encoded_metric_name[brace_index:])
            metric_name = encoded_metric_name[:brace_index].strip()
        except Exception as err:
            raise ValueError("Failed to parse the encoded_metric_name %s, invalid format"
                             % encoded_metric_name, err)
    return metric_name, metric_tags
