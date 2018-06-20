#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import sys

import magic
import os
import warnings
import json
import magic
import requests
from requests.auth import AuthBase

from thehive4py.models import CaseHelper
from thehive4py.query import *
from thehive4py.exceptions import *


class BearerAuth(AuthBase):
    """
        A custom authentication class for requests

        :param api_key: The API Key to use for the authentication
    """
    def __init__(self, api_key):
        self.api_key = api_key

    def __call__(self, req):
        req.headers['Authorization'] = 'Bearer {}'.format(self.api_key)
        return req


class TheHiveApi:

    """
        Python API for TheHive

        :param url: thehive URL
        :param principal: The username or the API key
        :param password: The password for basic authentication or None. Defaults to None
    """

    def __init__(self, url, principal, password=None, proxies={}, cert=True):

        self.url = url
        self.principal = principal
        self.password = password
        self.proxies = proxies

        if self.password is not None:
            self.auth = requests.auth.HTTPBasicAuth(self.principal,self.password)
        else:
            self.auth = BearerAuth(self.principal)

        self.cert = cert

        # Create a CaseHelper instance
        self.case = CaseHelper(self)

    def __find_rows(self, find_url, **attributes):
        """
            :param find_url: URL of the find api
            :type find_url: string
            :return: The Response returned by requests including the list of documents based on find_url
            :rtype: Response object
        """
        req = self.url + find_url

        # Add range and sort parameters
        params = {
            "range": attributes.get("range", "all"),
            "sort": attributes.get("sort", [])
        }

        # Add body
        data = {
            "query": attributes.get("query", {})
        }

        try:
            return requests.post(req, params=params, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise TheHiveException("Error: {}".format(e))

    def do_patch(self, api_url, **attributes):
        return requests.patch(self.url + api_url, headers={'Content-Type': 'application/json'}, json=attributes,
                              proxies=self.proxies, auth=self.auth, verify=self.cert)

    def create_case(self, case):

        """
        :param case: The case details
        :type case: Case defined in models.py
        :return: TheHive case
        :rtype: json
        """

        req = self.url + "/api/case"
        data = case.jsonify()
        try:
            return requests.post(req, headers={'Content-Type': 'application/json'}, data=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseException("Case create error: {}".format(e))

    def update_case(self, case, fields=[]):
        """
        Update a case.
        :param case: The case to update. The case's `id` determines which case to update.
        :param fields: Optional parameter, an array of fields names, the ones we want to update
        :return:
        """
        req = self.url + "/api/case/{}".format(case.id)

        # Choose which attributes to send
        update_keys = [
            'title', 'description', 'severity', 'startDate', 'owner', 'flag', 'tlp', 'tags', 'resolutionStatus',
            'impactStatus', 'summary', 'endDate', 'metrics', 'status', 'customFields', 'metrics'
        ]
        #data = {k: v for k, v in case.iteritems() if (len(fields) > 0 and k in fields) or (len(fields) == 0 and k in update_keys)}
        data = {k: v for k, v in case.__dict__.items() if (len(fields) > 0 and k in fields) or (len(fields) == 0 and k in update_keys)}

        try:
            return requests.patch(req, headers={'Content-Type': 'application/json'}, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseException("Case update error: {}".format(e))

    def create_case_task(self, case_id, case_task):

        """
        :param case_id: Case identifier
        :param case_task: TheHive task
        :type case_task: CaseTask defined in models.py
        :return: TheHive task
        :rtype: json

        """

        req = self.url + "/api/case/{}/task".format(case_id)
        data = case_task.jsonify()

        try:
            return requests.post(req, headers={'Content-Type': 'application/json'}, data=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseTaskException("Case task create error: {}".format(e))

    def update_case_task(self, task):
        """
        :Updates TheHive Task
        :param case: The task to update. The task's `id` determines which Task to update.
        :return:
        """
        req = self.url + "/api/case/task/{}".format(task.id)

        # Choose which attributes to send
        update_keys = [
            'title', 'description', 'status', 'order', 'user', 'owner', 'flag', 'startDate', 'endDate'
        ]

        data = {k: v for k, v in task.__dict__.items() if k in update_keys}

        try:
            return requests.patch(req, headers={'Content-Type': 'application/json'}, json=data,
                                  proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseTaskException("Case task update error: {}".format(e))

    def create_task_log(self, task_id, case_task_log):

        """
        :param task_id: Task identifier
        :param case_task_log: TheHive log
        :type case_task_log: CaseTaskLog defined in models.py
        :return: TheHive log
        :rtype: json
        """

        req = self.url + "/api/case/task/{}/log".format(task_id)
        data = {'_json': json.dumps({"message":case_task_log.message})}

        if case_task_log.file:
            f = {'attachment': (os.path.basename(case_task_log.file), open(case_task_log.file, 'rb'), magic.Magic(mime=True).from_file(case_task_log.file))}
            try:
                return requests.post(req, data=data,files=f, proxies=self.proxies, auth=self.auth, verify=self.cert)
            except requests.exceptions.RequestException as e:
                raise CaseTaskException("Case task log create error: {}".format(e))
        else:
            try:
                return requests.post(req, headers={'Content-Type': 'application/json'}, data=json.dumps({'message':case_task_log.message}), proxies=self.proxies, auth=self.auth, verify=self.cert)
            except requests.exceptions.RequestException as e:
                raise CaseTaskException("Case task log create error: {}".format(e))

    def create_case_observable(self, case_id, case_observable):

        """
        :param case_id: Case identifier
        :param case_observable: TheHive observable
        :type case_observable: CaseObservable defined in models.py
        :return: TheHive observable
        :rtype: json
        """

        req = self.url + "/api/case/{}/artifact".format(case_id)

        if case_observable.dataType == 'file':
            try:
                mesg = json.dumps({ "dataType": case_observable.dataType,
                    "message": case_observable.message,
                    "tlp": case_observable.tlp,
                    "tags": case_observable.tags,
                    "ioc": case_observable.ioc
                    })
                data = {"_json": mesg}
                return requests.post(req, data=data, files=case_observable.data[0], proxies=self.proxies, auth=self.auth, verify=self.cert)
            except requests.exceptions.RequestException as e:
                raise CaseObservableException("Case observable create error: {}".format(e))
        else:
            try:
                return requests.post(req, headers={'Content-Type': 'application/json'}, data=case_observable.jsonify(), proxies=self.proxies, auth=self.auth, verify=self.cert)
            except requests.exceptions.RequestException as e:
                raise CaseObservableException("Case observable create error: {}".format(e))

    def get_case(self, case_id):
        """
            :param case_id: Case identifier
            :return: TheHive case
            :rtype: json
        """
        req = self.url + "/api/case/{}".format(case_id)

        try:
            return requests.get(req, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseException("Case fetch error: {}".format(e))

    def find_cases(self, **attributes):
        return self.__find_rows("/api/case/_search", **attributes)

    def find_first(self, **attributes):
        """
            :return: first case of result set given by query
            :rtype: dict
        """
        return self.find_cases(**attributes).json()[0]

    def get_case_observables(self, case_id, **attributes):

        """
        :param case_id: Case identifier
        :return: list of observables
        ;rtype: json
        """

        req = self.url + "/api/case/artifact/_search"

        # Add range and sort parameters
        params = {
            "range": attributes.get("range", "all"),
            "sort": attributes.get("sort", [])
        }

        # Add body
        parent_criteria = Parent('case', Id(case_id))

        # Append the custom query if specified
        if "query" in attributes:
            criteria = And(parent_criteria, attributes["query"])
        else:
            criteria = parent_criteria

        data = {
            "query": criteria
        }

        try:
            return requests.post(req, params=params, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseObservableException("Case observables search error: {}".format(e))

    def get_case_tasks(self, case_id, **attributes):
        req = self.url + "/api/case/task/_search"

        # Add range and sort parameters
        params = {
            "range": attributes.get("range", "all"),
            "sort": attributes.get("sort", [])
        }

        # Add body
        parent_criteria = Parent('case', Id(case_id))

        # Append the custom query if specified
        if "query" in attributes:
            criteria = And(parent_criteria, attributes["query"])
        else:
            criteria = parent_criteria

        data = {
            "query": criteria
        }

        try:
            return requests.post(req, params=params, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseTaskException("Case tasks search error: {}".format(e))

    def get_linked_cases(self, case_id):
        """
        :param case_id: Case identifier
        :return: TheHive case(s)
        :rtype: json
        """
        req = self.url + "/api/case/{}/links".format(case_id)

        try:
            return requests.get(req, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseException("Linked cases fetch error: {}".format(e))

    def get_case_template(self, name):

        """
        :param name: Case template name
        :return: TheHive case template
        :rtype: json

        """

        req = self.url + "/api/case/template/_search"
        data = {
            "query": And(Eq("name", name), Eq("status", "Ok"))
        }

        try:
            response = requests.post(req, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
            json_response = response.json()

            if response.status_code == 200 and len(json_response) > 0:
                return response.json()[0]
            else:
                raise CaseTemplateException("Case template fetch error: Unable to find case template {}".format(name))
        except requests.exceptions.RequestException as e:
            raise CaseTemplateException("Case template fetch error: {}".format(e))

    def create_case_template(self, case_template):

        """
        :param case_template: TheHive Case Template
        :return: TheHive case template Id
        :rtype: string

        """

        req = self.url + "/api/case/template"
        data = case_template.jsonify()

        try:
            response = requests.post(req, headers={'Content-Type': 'application/json'}, data=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
            json_response = response.json()

            if response.status_code == 201 and len(json_response) > 0:
                return json_response
            else:
                sys.exit("Error: {}".format("Unable to create the case template"))
        except requests.exceptions.RequestException as e:
            sys.exit("Error: {}".format(e))

    def delete_case_template(self, caseId):

        """
        :param fieldId: Case template Id to delete
        :rtype: bool
        """

        req = self.url + "/api/case/template/{}".format(caseId)

        try:
            response = requests.delete(req, proxies=self.proxies, auth=self.auth, verify=self.cert)

            if response.status_code == 200 or response.status_code == 204:
                return True
            else:
                sys.exit("Error: {}".format("Error when attempting to delete case template."))

        except requests.exceptions.RequestException as e:
            sys.exit("Error: {}".format(e))

    def get_task_logs(self, task_id, **attributes):

        """
        :param taskId: Task identifier
        :type caseTaskLog: CaseTaskLog defined in models.py
        :return: TheHive logs
        :rtype: json
        """

        req = self.url + "/api/case/task/log/_search"

        # Add range and sort parameters
        params = {
            "range": attributes.get("range", "all"),
            "sort": attributes.get("sort", [])
        }

        # Add body
        parent_criteria = Parent('case_task', Id(task_id))

        # Append the custom query if specified
        if "query" in attributes:
            criteria = And(parent_criteria, attributes["query"])
        else:
            criteria = parent_criteria

        data = {
            "query": criteria
        }

        try:
            return requests.post(req, params=params, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseTaskException("Case task logs search error: {}".format(e))

    def create_custom_field(self, custom_field):

        """
        :param custom_field: TheHive custom field
        :type customfield: CustomField defined in models.py
        :rtype: json
        """

        req = self.url + "/api/list/custom_fields/_exists"

        data = {
            "key": "reference",
            "value": custom_field['reference']
        }

        try:
            response = requests.post(req, headers={'Content-Type': 'application/json'}, json=data,
                                     proxies=self.proxies, auth=self.auth, verify=self.cert)
            json_response = response.json()

            if response.status_code == 200 and len(json_response) > 0:
                exists = response.json()
            else:
                raise CustomFieldException("CustomField creation error: Unable to determine if custom field exists.")

        except requests.exceptions.RequestException as e:
            raise CustomFieldException("CustomField creation error: {}".format(e))

        if exists['found']:
            raise CustomFieldException("CustomField creation error: Cannot create custom field. "
                                       "The custom field reference already exists.")
        else:
            req = self.url + "/api/list/custom_fields"

            data = {
                "value": {
                    "name": custom_field['name'],
                    "reference": custom_field['reference'],
                    "description": custom_field['description'],
                    "type": custom_field['type'],
                    "options": custom_field['options']
                }
            }

            try:
                response = requests.post(req, headers={'Content-Type': 'application/json'}, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
                json_response = response.json()

                if response.status_code == 200 and len(json_response) > 0:
                    return response.json()
                else:
                    raise CustomFieldException("CustomField creation error: Unable to create custom field.")

            except requests.exceptions.RequestException as e:
                raise CustomFieldException("CustomField creation error: {}".format(e))

    def delete_custom_field(self, fieldId):

        """
        :param fieldId: Custom field Id to delete
        :rtype: bool
        """

        req = self.url + "/api/list/{}".format(fieldId)

        try:
            response = requests.delete(req, proxies=self.proxies, auth=self.auth, verify=self.cert)

            if response.status_code == 200 or response.status_code == 204:
                return True
            else:
                raise CustomFieldException("CustomField deletion error: Error when attempting to remove custom field.")

        except requests.exceptions.RequestException as e:
            raise CustomFieldException("CustomField deletion error: {}".format(e))

    def create_metric(self, metric):

        """
        :param metric: TheHive metric
        :type metric: Metric defined in models.py
        :return: TheHive metric
        :rtype: json
        """

        req = self.url + "/api/list/case_metrics"

        data = {
            "value": {
                "name": metric.name,
                "title": metric.title,
                "description": metric.description,
            }
        }

        try:
            response = requests.post(req, headers={'Content-Type': 'application/json'}, json=data, proxies=self.proxies,
                                     auth=self.auth, verify=self.cert)
            json_response = response.json()

            if response.status_code == 200 and len(json_response) > 0:
                return response.json()
            else:
                sys.exit("Error: {}".format("Unable to create metric."))

        except requests.exceptions.RequestException as e:
            sys.exit("Error: {}".format(e))

    def delete_metric(self, metricId):

        """
        :param metricId: Metric Id to delete
        :return: response
        :rtype: json
        """

        req = self.url + "/api/list/{}".format(metricId)

        try:
            response = requests.delete(req, proxies=self.proxies, auth=self.auth, verify=self.cert)

            if response.status_code == 200 or response.status_code == 204:
                return True
            else:
                sys.exit("Error: {}".format("Error when attempting to remove metric."))

        except requests.exceptions.RequestException as e:
            sys.exit("Error: {}".format(e))

    def create_alert(self, alert):

        """
        :param alert: TheHive alert
        :type alert: Alert defined in models.py
        :return: TheHive alert
        :rtype: json
        """

        req = self.url + "/api/alert"
        data = alert.jsonify()
        try:
            return requests.post(req, headers={'Content-Type': 'application/json'}, data=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise AlertException("Alert create error: {}".format(e))

    def update_alert(self, alert_id, alert, fields=[]):
        """
        Update an alert.
        :param alert_id: The ID of the alert to update.
        :param data: The alert to update.
        :param fields: Optional parameter, an array of fields names, the ones we want to update
        :return:
        """
        req = self.url + "/api/alert/{}".format(alert_id)

        # update only the alert attributes that are not read-only
        update_keys = ['tlp', 'severity', 'tags', 'caseTemplate', 'title', 'description']

        data = {k: v for k, v in alert.__dict__.items() if
                (len(fields) > 0 and k in fields) or (len(fields) == 0 and k in update_keys)}

        if hasattr(alert, 'artifacts'):
            data['artifacts'] = [a.__dict__ for a in alert.artifacts]
        try:
            return requests.patch(req, headers={'Content-Type': 'application/json'}, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException:
            raise AlertException("Alert update error: {}".format(e))

    def get_alert(self, alert_id):
        """
            :param alert_id: Alert identifier
            :return: TheHive Alert
            :rtype: json
        """
        req = self.url + "/api/alert/{}".format(alert_id)

        try:
            return requests.get(req, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise AlertException("Alert fetch error: {}".format(e))

    def find_alerts(self, **attributes):
        """
            :return: list of Alerts
            :rtype: json
        """

        return self.__find_rows("/api/alert/_search", **attributes)

    def run_analyzer(self, cortex_id, artifact_id, analyzer_id):

        """
        :param cortex_id: identifier of the Cortex server
        :param artifact_id: identifier of the artifact as found with an artifact search
        :param analyzer_id: name of the analyzer used by the job
        :rtype: json
        """

        req = self.url + "/api/connector/cortex/job"

        try:
            data = json.dumps({ "cortexId": cortex_id,
                "artifactId": artifact_id,
                "analyzerId": analyzer_id
                })
            return requests.post(req, headers={'Content-Type': 'application/json'}, data=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise TheHiveException("Analyzer run error: {}".format(e))

    def find_cortex_jobs(self, artifact_id, analyzer_id='', **attributes):

        """
        :param artifact_id: Artifact / Observable ID
        :param analyzer_id: Analyzer ID (E.g. VirusTotal_GetReport_3_0)
        :type caseArtifactJob:
        :return: Cortex Jobs
        :rtype: json
        """

        req = self.url + "/api/connector/cortex/job/_search"

        # Add range and sort parameters
        params = {
            "range": attributes.get("range", "all"),
            "sort": attributes.get("sort", [])
        }

        parent_criteria = Parent('case_artifact', Id(artifact_id))

        analyzer = {
            "analyzerId": analyzer_id
        }

        if analyzer_id:
            criteria = And(parent_criteria, analyzer)
        else:
            criteria = parent_criteria

        data = {
            "query": criteria
        }

        try:
            return requests.post(req, params=params, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseException("Unable to query TheHive Cortex connector for jobs: {}".format(e))

    def retrieve_cortex_job(self, job_id, artifact_id):

        req = self.url + "/api/connector/cortex/job/{}".format(job_id)

        parent_criteria = Parent('case_artifact', Id(artifact_id))

        data = {
            "query": parent_criteria
        }

        try:
            return requests.get(req, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)
        except requests.exceptions.RequestException as e:
            raise CaseException("Unable to retrieve Cortex job: {}".format(e))

    def create_observable_datatype(self, data_type):

        """
        :param data_type: data type to create
        :return: Data type uid
        :rtype: json
        """

        req = self.url + "/api/list/list_artifactDataType"

        if data_type:
            data = {"value": data_type}

            try:
                response = requests.post(req, headers={'Content-Type': 'application/json'}, json=data, proxies=self.proxies, auth=self.auth, verify=self.cert)

                if response.status_code == 200:
                    return response.json()
                else:
                    raise CaseObservableException("Unable to create observable data type: {}".format(response))
            except requests.exceptions.RequestException as e:
                raise CaseObservableException("Unable to create observable data type: {}".format(e))
        else:
            raise CaseObservableException("Unable to create data type. No data type provided")

    def delete_observable_datatype(self, type_id):

        """
        :param data_type: data type to create
        :return: Data type uid
        :rtype: json
        """

        req = self.url + "/api/list/{}".format(type_id)

        try:
            response = requests.delete(req, headers={'Content-Type': 'application/json'}, proxies=self.proxies, auth=self.auth, verify=self.cert)

            if response.status_code == 204:
                return True
            else:
                raise CaseObservableException("Unable to delete observable data type: {}".format(response))
        except requests.exceptions.RequestException as e:
            raise CaseObservableException("Unable to delete observable data type {}: {}".format(type_id, e))

    def retrieve_datastore_content(self, content_id, zip=False):
        """
            :param content_id: datastore content id
            :return: content
            :rtype: binary
        """
        if zip:
            req = self.url + "/api/datastorezip/{}".format(content_id, zip=False)
        else:
            req = self.url + "/api/datastore/{}".format(content_id, zip=False)

        try:
            response = requests.get(req, proxies=self.proxies, auth=self.auth, verify=self.cert)
            if response.status_code == 200:
                return response
        except requests.exceptions.RequestException as e:
            raise CaseException("Case fetch error: {}".format(e))

# TODO Add method for create_observable_datatype - POST, URI: /api/list/list_artifactDataType, JSON: {"value":"test-type"}
# - addObservable(file)
# - addObservable(data)