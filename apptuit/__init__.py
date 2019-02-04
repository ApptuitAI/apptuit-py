APPTUIT_PY_TOKEN = "APPTUIT_API_TOKEN"
APPTUIT_PY_TAGS = "APPTUIT_TAGS"
DEPRECATED_APPTUIT_PY_TOKEN = "APPTUIT_PY_TOKEN"
DEPRECATED_APPTUIT_PY_TAGS = "APPTUIT_PY_TAGS"

from .apptuit_client import Apptuit, DataPoint, ApptuitException, ApptuitSendException, \
    TimeSeriesName, TimeSeries
from apptuit import pyformance, timeseries

__version__ = '1.4.0'

__all__ = ['Apptuit', 'DataPoint', 'ApptuitException', 'TimeSeriesName', 'TimeSeries',
           'pyformance', 'timeseries', 'ApptuitSendException']
