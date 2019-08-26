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
Tests for the query API
"""

import sys

from requests import Response

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch

from nose.tools import assert_is_not_none, assert_is_none, assert_equals, assert_true, assert_raises
import pandas as pd
import requests
from apptuit import Apptuit, ApptuitException, apptuit_client


def get_mock_response():
    """
    Returns a mock response for the get request
    """
    with open('tests/response.json') as f:
        return f.readlines()[0]


def test_api_endpoint_param():
    """
        Test the api_endpoint param of apptuit client
    """
    _ = Apptuit(sanitize_mode=None, token="test_token", api_endpoint="https://api.apptuit.ai/")
    with assert_raises(ValueError):
        _ = Apptuit(sanitize_mode=None, token="test_token", api_endpoint=None)
    with assert_raises(ValueError):
        _ = Apptuit(sanitize_mode=None, token="test_token", api_endpoint="")


def do_query(mock_get):
    """
    Execute the query API and return the mock response
    """
    mock_get.return_value.content = get_mock_response()
    mock_get.return_value.status_code = 200
    token = 'sdksdk203afdsfj_sadasd3939'
    client = Apptuit(sanitize_mode=None, token=token)
    query = "fetch('nyc.taxi.rides')"
    start = 1406831400
    end = 1407609000
    return client.query(query, start, end)


@patch('apptuit.apptuit_client.requests.get')
def test_query(mock_get):
    """
    Test a valid query and make sure results are returned
    """
    resp = do_query(mock_get)
    assert_is_not_none(resp[0])


@patch('apptuit.apptuit_client.requests.get')
def test_query_result_number_index(mock_get):
    """
    Test that we can access the output by number based indexing from
    the query result
    """
    resp = do_query(mock_get)
    df = resp[0].to_df()
    assert_is_not_none(df)


@patch('apptuit.apptuit_client.requests.get')
def test_query_result_string_index(mock_get):
    """
    Test that we can access the output by the name of the metric from the
    query result
    """
    resp = do_query(mock_get)
    df = resp["nyc.taxi.rides"].to_df()
    assert_is_not_none(df)


@patch('apptuit.apptuit_client.requests.get')
def test_df_shape(mock_get):
    """
    Verify the dataframe shape
    """
    resp = do_query(mock_get)
    df = resp[0].to_df()
    assert_equals(df.shape, (433, 1))


@patch('apptuit.apptuit_client.requests.get')
def test_number_of_series(mock_get):
    """
    Verify the number of time series in the query result
    """
    resp = do_query(mock_get)
    assert_equals(len(resp[0].series), 1)


@patch('apptuit.apptuit_client.requests.get')
def test_data(mock_get):
    """
    Verify the data returned from the query
    """
    expected_df = pd.read_csv('tests/nyc.taxi.rides.csv', index_col=0, header=0, parse_dates=True)
    resp = do_query(mock_get)
    df = resp[0].to_df()
    assert_true(df.equals(expected_df))


@patch('apptuit.apptuit_client.requests.get')
def test_metadata(mock_get):
    """
    Test that the metadata of the query results are as expected
    """
    expected_series_name = "nyc.taxi.rides"
    expected_tags = {"host": "localhost"}
    resp = do_query(mock_get)
    series = resp[0].series[0]
    assert_equals(series.name.metric, expected_series_name)
    assert_equals(series.name.tags, expected_tags)


@patch('apptuit.apptuit_client.requests.get')
def test_multiple_retries(mock_get):
    """
    Test that the query API attempts retries when an error is returned from
    the backend API. Since we patch the status code as 504 and create an HTTPError
    as a side effect of the get call, we cannot verify that the retries succeed.
    """
    mock_get.return_value.content = get_mock_response()
    mock_get.return_value.status_code = 504
    mock_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError
    token = 'sdksdk203afdsfj_sadasd3939'
    client = Apptuit(sanitize_mode=None, token=token)
    query = "fetch('nyc.taxi.rides')"
    start = 1406831400
    end = 1407609000
    with assert_raises(ApptuitException):
        client.query(query, start, end, retry_count=3)

@patch('apptuit.apptuit_client.requests.get')
def test_multiple_retries_conn_err(mock_get):
    """
    Test that the query API attempts retries when an error is returned from
    the backend API. Since we patch the status code as 504 and create an HTTPError
    as a side effect of the get call, we cannot verify that the retries succeed.
    """
    mock_get.side_effect = requests.exceptions.ConnectionError
    token = 'sdksdk203afdsfj_sadasd3939'
    client = Apptuit(sanitize_mode=None, token=token)
    query = "fetch('nyc.taxi.rides')"
    start = 1406831400
    end = 1407609000
    with assert_raises(requests.exceptions.ConnectionError):
        client.query(query, start, end, retry_count=3)
    assert_equals(mock_get.call_count, 4)


@patch('apptuit.apptuit_client.requests.get')
def test_get_error_with_no_retry(mock_get):
    """
    Test that when the retry_count is 0 for the query API we get an exception
    """
    mock_get.return_value.content = get_mock_response()
    mock_get.return_value.status_code = 504
    err_response = Response()
    err_response.status_code = 504
    mock_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError(response=err_response)
    token = 'sdksdk203afdsfj_sadasd3939'
    client = Apptuit(sanitize_mode=None, token=token)
    query = "fetch('nyc.taxi.rides')"
    start = 1406831400
    end = 1407609000
    with assert_raises(ApptuitException):
        client.query(query, start, end, retry_count=0)
    assert_equals(1, mock_get.call_count)

@patch('apptuit.apptuit_client.requests.get')
def test_get_error_with_retry(mock_get):
    """
    Test that when the retry_count is 0 for the query API we get an exception
    """
    mock_get.return_value.content = get_mock_response()
    mock_get.return_value.status_code = 504
    err_response = Response()
    err_response.status_code = 504
    mock_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError(response=err_response)
    token = 'sdksdk203afdsfj_sadasd3939'
    client = Apptuit(sanitize_mode=None, token=token)
    query = "fetch('nyc.taxi.rides')"
    start = 1406831400
    end = 1407609000
    with assert_raises(ApptuitException):
        client.query(query, start, end, retry_count=1)
    assert_equals(2, mock_get.call_count)


@patch('apptuit.apptuit_client.requests.get')
def test_get_error_retry_with_404(mock_get):
    """
    Test that when the retry_count is 0 for the query API we get an exception
    """
    mock_get.return_value.content = get_mock_response()
    mock_get.return_value.status_code = 404
    err_response = Response()
    err_response.status_code = 404
    mock_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError(response=err_response)
    token = 'sdksdk203afdsfj_sadasd3939'
    client = Apptuit(sanitize_mode=None, token=token)
    query = "fetch('nyc.taxi.rides')"
    start = 1406831400
    end = 1407609000
    with assert_raises(ApptuitException):
        client.query(query, start, end, retry_count=2)
    assert_equals(1, mock_get.call_count)

@patch('apptuit.apptuit_client.requests.get')
def test_get_error_retry_with_SSLError(mock_get):
    """
    Test that when the retry_count is 0 for the query API we get an exception
    """
    mock_get.return_value.content = get_mock_response()
    mock_get.return_value.status_code = 404
    err_response = Response()
    err_response.status_code = 505
    mock_get.return_value.raise_for_status.side_effect = requests.exceptions.SSLError(response=err_response)
    token = 'sdksdk203afdsfj_sadasd3939'
    client = Apptuit(sanitize_mode=None, token=token)
    query = "fetch('nyc.taxi.rides')"
    start = 1406831400
    end = 1407609000
    with assert_raises(ApptuitException):
        client.query(query, start, end, retry_count=2)
    assert_equals(1, mock_get.call_count)


@patch('apptuit.apptuit_client.requests.get')
def test_empty_dps(mock_get):
    """
    Test that we get an exception if the dps array is empty in the JSON response
    """
    mock_get.return_value.content = '{"outputs":[{"id":"nyc:taxi:rides","result":[{ \
                                    "metric":"nyc.taxi.rides","tags":{"host":"localhost"}, \
                                    "aggregatedTags":[],"dps":[]}]}], \
                                    "hints":[],"query": {"querytext":"fetch(\'nyc.taxi.rides\')", \
                                    "startTime":1406831400, \
                                    "startTimeHumanReadableSYS":"July 31, 2014 6:30:00 PM UTC", \
                                    "startTimeHumanReadableIST":"August 1, 2014 12:00:00 AM IST", \
                                    "endTime":1407609000, "endTimeHumanReadableSYS":"August 9,2014 6:30:00 PM UTC", \
                                    "endTimeHumanReadableIST":"August 10, 2014 12:00:00 AM IST", \
                                    "digest":"Mdt8e+HDjnGByMMJdEnTnNdUxKo=:60845", "optionsdigest":"", \
                                    "options":"{}"},"query_stats":{"compactedRows":217, "processedRows":217, \
                                    "dataPointsProcessed":219, "numSeries":1, "queryTimeMillis":152, \
                                    "hbaseTimeMillis":21},"timing_diagnostics": \
                                    [{"tag":"QUERY_EXECUTION_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":152},{"tag":"AST_BUILD_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":29}, \
                                    {"tag":"AST_JYTHON_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":29},{"tag":"STATEMENT_VALIDATION_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":0}, \
                                    {"tag":"PLAN_BUILDING_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":0},{"tag":"QUERY_OPTIMIZATION_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":0}, \
                                    {"tag":"PLAN_EXECUTION_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":106},{"tag":"SCHEMA_SERVICE_FETCH_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":93}, \
                                    {"tag":"DATASOURCE_FETCH_RUN_TIME", "instanceCount":2, \
                                    "totalElapsedTimeMillis":32},{"tag":"TSD_HBASE_TIME", \
                                    "instanceCount":2, "totalElapsedTimeMillis":21}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_TIME", "instanceCount":2, \
                                    "totalElapsedTimeMillis":52},{"tag":"DATASOURCE_FETCH_DP_DECODE_GET_TAGS_TIME", \
                                    "instanceCount":2, "totalElapsedTimeMillis":51}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_GET_DPS_TIME", "instanceCount":2, \
                                    "totalElapsedTimeMillis":0},{"tag":"DATASOURCE_FETCH_DP_DECODE_CORE_PROCESSING_TIME", \
                                    "instanceCount":4, "totalElapsedTimeMillis":0}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_DS_WAIT_TIME", "instanceCount":4, \
                                    "totalElapsedTimeMillis":0},{"tag":"DATASOURCE_FETCH_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":12}, \
                                    {"tag":"PLAN_EXECUTION_JPY_REMOVE_DF_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":17},{"tag":"RESULT_DATA_MARSHALLING_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":0}]}'
    mock_get.return_value.status_code = 200
    token = 'sdksdk203afdsfj_sadasd3939'
    client = Apptuit(sanitize_mode=None, token=token)
    query = "fetch('nyc.taxi.rides')"
    start = 1406831400
    end = 1407609000
    client.query(query, start, end)


@patch('apptuit.apptuit_client.requests.get')
def test_empty_output(mock_get):
    """
    Test the case when the outputs array is empty in the response
    """
    mock_get.return_value.content = '{"outputs":[],"hints":[],"query": \
                                    {"querytext":"fetch(\'nyc.taxi.rides\')", \
                                    "startTime":1406831400, "startTimeHumanReadableSYS":"July 31, 2014 6:30:00 PM UTC", \
                                    "startTimeHumanReadableIST":"August 1, 2014 12:00:00 AM IST", "endTime":1407609000, \
                                    "endTimeHumanReadableSYS":"August 9, 2014 6:30:00 PM UTC", \
                                    "endTimeHumanReadableIST":"August 10, 2014 12:00:00 AM IST", \
                                    "digest":"Mdt8e+HDjnGByMMJdEnTnNdUxKo=:60845", "optionsdigest":"", \
                                    "options":"{}"},"query_stats":{"compactedRows":217, "processedRows":217, \
                                    "dataPointsProcessed":219, "numSeries":1, "queryTimeMillis":152, \
                                    "hbaseTimeMillis":21},"timing_diagnostics": \
                                    [{"tag":"QUERY_EXECUTION_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":152},{"tag":"AST_BUILD_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":29}, \
                                    {"tag":"AST_JYTHON_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":29},{"tag":"STATEMENT_VALIDATION_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":0}, \
                                    {"tag":"PLAN_BUILDING_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":0},{"tag":"QUERY_OPTIMIZATION_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":0}, \
                                    {"tag":"PLAN_EXECUTION_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":106},{"tag":"SCHEMA_SERVICE_FETCH_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":93}, \
                                    {"tag":"DATASOURCE_FETCH_RUN_TIME", "instanceCount":2, \
                                    "totalElapsedTimeMillis":32},{"tag":"TSD_HBASE_TIME", \
                                    "instanceCount":2, "totalElapsedTimeMillis":21}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_TIME", "instanceCount":2, \
                                    "totalElapsedTimeMillis":52},{"tag":"DATASOURCE_FETCH_DP_DECODE_GET_TAGS_TIME", \
                                    "instanceCount":2, "totalElapsedTimeMillis":51}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_GET_DPS_TIME", \
                                    "instanceCount":2, "totalElapsedTimeMillis":0}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_CORE_PROCESSING_TIME", \
                                    "instanceCount":4, "totalElapsedTimeMillis":0}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_DS_WAIT_TIME", \
                                    "instanceCount":4, "totalElapsedTimeMillis":0}, \
                                    {"tag":"DATASOURCE_FETCH_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":12},{"tag":"PLAN_EXECUTION_JPY_REMOVE_DF_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":17}, \
                                    {"tag":"RESULT_DATA_MARSHALLING_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":0}]}'
    mock_get.return_value.status_code = 200
    token = 'sdksdk203afdsfj_sadasd3939'
    client = Apptuit(sanitize_mode=None, token=token)
    query = "fetch('nyc.taxi.rides')"
    start = 1406831400
    end = 1407609000
    resp = client.query(query, start, end)
    assert_is_none(resp)


@patch('apptuit.apptuit_client.requests.get')
def test_empty_results(mock_get):
    """
    Test that when results array is empty in the response and we try to access the
    outputs in the results object we get a KeyError
    """
    mock_get.return_value.content = '{"outputs":[{"id":"nyc:taxi:rides", \
                                    "result":[]}],"hints":[],"query": \
                                    {"querytext":"fetch(\'nyc.taxi.rides\')", \
                                    "startTime":1406831400, \
                                    "startTimeHumanReadableSYS":"July 31, 2014 6:30:00 PM UTC", \
                                    "startTimeHumanReadableIST":"August 1, 2014 12:00:00 AM IST", \
                                    "endTime":1407609000, \
                                    "endTimeHumanReadableSYS":"August 9, 2014 6:30:00 PM UTC", \
                                    "endTimeHumanReadableIST":"August 10, 2014 12:00:00 AM IST", \
                                    "digest":"Mdt8e+HDjnGByMMJdEnTnNdUxKo=:60845", \
                                    "optionsdigest":"", "options":"{}"}, \
                                    "query_stats":{"compactedRows":217, "processedRows":217, \
                                    "dataPointsProcessed":219, "numSeries":1, "queryTimeMillis":152, \
                                    "hbaseTimeMillis":21}, \
                                    "timing_diagnostics":[{"tag":"QUERY_EXECUTION_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":152}, \
                                    {"tag":"AST_BUILD_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":29},{"tag":"AST_JYTHON_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":29}, \
                                    {"tag":"STATEMENT_VALIDATION_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":0}, \
                                    {"tag":"PLAN_BUILDING_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":0},{"tag":"QUERY_OPTIMIZATION_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":0}, \
                                    {"tag":"PLAN_EXECUTION_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":106},{"tag":"SCHEMA_SERVICE_FETCH_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":93}, \
                                    {"tag":"DATASOURCE_FETCH_RUN_TIME", "instanceCount":2, \
                                    "totalElapsedTimeMillis":32},{"tag":"TSD_HBASE_TIME", \
                                    "instanceCount":2, "totalElapsedTimeMillis":21}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_TIME", "instanceCount":2, \
                                    "totalElapsedTimeMillis":52}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_GET_TAGS_TIME", \
                                    "instanceCount":2, "totalElapsedTimeMillis":51}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_GET_DPS_TIME", \
                                    "instanceCount":2, "totalElapsedTimeMillis":0}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_CORE_PROCESSING_TIME", \
                                    "instanceCount":4, "totalElapsedTimeMillis":0}, \
                                    {"tag":"DATASOURCE_FETCH_DP_DECODE_DS_WAIT_TIME", \
                                    "instanceCount":4, "totalElapsedTimeMillis":0}, \
                                    {"tag":"DATASOURCE_FETCH_TOTAL_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":12}, \
                                    {"tag":"PLAN_EXECUTION_JPY_REMOVE_DF_TOTAL_TIME", \
                                    "instanceCount":1, "totalElapsedTimeMillis":17}, \
                                    {"tag":"RESULT_DATA_MARSHALLING_TIME", "instanceCount":1, \
                                    "totalElapsedTimeMillis":0}]}'
    mock_get.return_value.status_code = 200
    token = 'sdksdk203afdsfj_sadasd3939'
    client = Apptuit(sanitize_mode=None, token=token)
    query = "fetch('nyc.taxi.rides')"
    start = 1406831400
    end = 1407609000
    resp = client.query(query, start, end)
    with assert_raises(KeyError):
        _ = resp[0]

def test_timeseries_obj_creation():
    """
        Negative test cases for TimeSeries object when either index or
        values is missing (not both at the same time)
    """
    with assert_raises(ValueError):
        apptuit_client.TimeSeries('metric', {}, values=[3.14])

    with assert_raises(ValueError):
        apptuit_client.TimeSeries('metric', {}, index=[123456])

    with assert_raises(ValueError):
        apptuit_client.TimeSeries('metric', {}, index=[123455, 123456], values=[3.14])

    with assert_raises(ValueError):
        apptuit_client.TimeSeries(metric=None, tags=None)


@patch('apptuit.apptuit_client.requests.get')
def test_missing_pandas(mock_get):
    orig_modules = sys.modules.copy()
    orig_pandas = orig_modules['pandas']
    orig_modules['pandas'] = None
    with patch.dict(sys.modules, orig_modules):
        if orig_pandas:
            sys.modules['pandas'] = None
        resp = do_query(mock_get)
        with assert_raises(ImportError):
            resp[0].to_df()
