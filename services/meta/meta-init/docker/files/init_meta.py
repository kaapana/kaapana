#!/usr/bin/env python3
# -*- coding: utf-8; mode: python; indent-tabs-mode: nil; -*-

import os
import elasticsearch
import requests
import traceback
import json
import socket
import time


def check_port(name, host, port, delay):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        while sock.connect_ex((host, int(port))) != 0:
            print("Wait for Service: %s  on host: %s and port: %s!" %
                  (name, host, port))
            time.sleep(delay)
        print("Service: %s  is READY!!!! host: %s and port: %s!" %
              (name, host, port))
        return 1

    except Exception as e:
        # print(e)
        print("Service: %s  host: %s is not known! Try again..." % (name, host))
        return 0


def delete_index(index_name, elastic_host, elastic_port):
    es = elasticsearch.Elasticsearch(
        [{'host': elastic_host, 'port': elastic_port}])
    if (es.indices.exists(index_name)):
        print("Deleting fileindex", index_name)
        res = es.indices.delete(index_name)


def recreate_index(index_name, elastic_host, elastic_port):
    """
    ToDo: Docstring.
    """
    es = elasticsearch.Elasticsearch(
        [{'host': elastic_host, 'port': elastic_port}])
    if not (es.indices.exists(index_name)):
        initialization_request = {
            "settings":
            {
                "number_of_shards": 2,
                "number_of_replicas": 0,
                # If true, malformed numbers/fields are ignored.
                # "index.mapping.ignore_malformed": True,
                # If false (default), malformed numbers/fields throw an exception and reject the whole document.
                # ToDo: ausprobieren und debuggen.
                "index.mapper.dynamic": True,
                # 3761 non-deprecated and non-private DICOM tags exist < 5000.
                "index.mapping.total_fields.limit": 6000,
                # default=100 ist zu wenig, 119 bei erster Fehlermeldung in Kibana.
                "index.max_docvalue_fields_search": 150
            },
            "mappings":
            {
                "_doc":
                {
                    "dynamic": 'true',
                    "date_detection": 'false',
                    "numeric_detection": 'false',
                    "dynamic_templates": [
                        {
                            "check_integer": {
                                "match_pattern": "regex",
                                "match": "^.*_integer.*$",
                                "mapping": {
                                    "type": "long"
                                }
                            }
                        },
                        {
                            "check_float": {
                                "match_pattern": "regex",
                                "match": "^.*_float.*$",
                                "mapping": {
                                    "type": "float"
                                }
                            }
                        },
                        {
                            "check_datetime": {
                                "match_pattern": "regex",
                                "match": "^.*_datetime.*$",
                                "mapping": {
                                    "type": "date",
                                    "format": "yyyy-MM-dd HH:mm:ss.SSSSSS"
                                }
                            }
                        },
                        {
                            "check_date": {
                                "match_pattern": "regex",
                                "match": "^.*_date.*$",
                                "mapping": {
                                    "type": "date",
                                    "format": "yyyy-MM-dd"
                                }
                            }
                        },
                        {
                            "check_time": {
                                "match_pattern": "regex",
                                "match": "^.*_time.*$",
                                "mapping": {
                                    "type": "date",
                                    "format": "HH:mm:ss.SSSSSS"
                                }
                            }
                        },
                        {
                            "check_timestamp": {
                                "match_pattern": "regex",
                                "match": "^.*timestamp.*$",
                                "mapping": {
                                    "type": "date",
                                    "format": "yyyy-MM-dd HH:mm:ss.SSSSSS"
                                }
                            }
                        },
                        {
                            "check_object": {
                                "match_pattern": "regex",
                                "match": "^.*_object.*$",
                                "mapping": {
                                    "type": "object"
                                }
                            }
                        },
                        {
                            "check_boolean": {
                                "match_pattern": "regex",
                                "match": "^.*_boolean.*$",
                                "mapping": {
                                    "type": "boolean"
                                }
                            }
                        },
                        {
                            "check_array": {
                                "match_pattern": "regex",
                                "match": "^.*_array.*$",
                                "mapping": {
                                    "type": "array"
                                }
                            }
                        }
                    ],
                }
            }
        }

        res = es.indices.create(index_name, initialization_request)
        print("################################################           Created elatic index!!")
    else:
        print("################################################           Index already exists")


def setup_kibana(kibana_dashboard, kibana_host, kibana_port):
    """
    ToDo: Docstring.
    """
    print("SETUP KIBANA")
    with open(kibana_dashboard) as f:
        jsonObj = json.load(f)

    for anObject in jsonObj:
        try:
            i_d = anObject['_id']
            t_ype = anObject['_type']
            s_ource = anObject['_source']
            resp = requests.post('http://' + kibana_host + ':' + str(kibana_port)
                                 + '/api/saved_objects/' + t_ype + '/' + i_d + '?overwrite={}'.format(override_objects), data='{"attributes":' + json.JSONEncoder().encode(s_ource) + '}', headers=kbn_xsrf)
            if resp.status_code == 200:
                print('{}: OK!'.format(s_ource['title']))

            else:
                print('Could not send Kibana dashboard! -> Status-code')
                print('{}: ERROR!'.format(s_ource['title']))
                print(resp.text)
                print(resp.content)
                exit(1)
        except Exception as e:
            logging.error(traceback.format_exc())
            print('Could not send Kibana dashboard! -> Exception')
            print('{}: ERROR!'.format(s_ource['title']))
            exit(1)
    return True

# TODO https://discuss.elastic.co/t/reloading-the-index-field-list-automatically/116687
# https://<domain>/meta/api/index_patterns/_fields_for_wildcard?pattern=meta-index&meta_fields=%5B%22_source%22%2C%22_id%22%2C%22_type%22%2C%22_index%22%2C%22_score%22%5D


def create_index_pattern(kibana_host, kibana_port):
    index_pattern = {
        "attributes": {"title": "{}".format(elastic_indexname),
                       "fieldFormatMap": "{\"0020000D StudyInstanceUID_keyword.keyword\":{\"id\":\"url\",\"params\":{\"urlTemplate\":\"https://"+domain+"/ohif/IHEInvokeImageDisplay?requestType=STUDY&studyUID={{value}}\",\"labelTemplate\":\"{{value}}\"}}}",
                       }
    }
    try:
        resp = requests.post('http://' + kibana_host + ':' + str(kibana_port) + '/api/saved_objects/index-pattern/{}'.format(elastic_indexname) +
                             '?overwrite={}'.format(override_objects), data=json.dumps(index_pattern), headers=kbn_xsrf)
        if resp.status_code == 200:
            print('Index-Pattern: OK!')
        else:
            print('Index-Pattern: Error!')
            print(resp.text)
            print(resp.content)
            exit(1)

    except Exception as e:
        logging.error(traceback.format_exc())
        print('Index-Pattern: Error!')
        exit(1)


print("Started init-container")
if __name__ == "__main__":
    print("provisioning...")
    init_kibana = os.getenv('INITKIBANA', False)
    init_elastic = os.getenv('INITELASTIC', False)
    stack_version = os.getenv('STACKVERSION', '6.8.12')
    override_objects = os.getenv('OVERRIDE_OBJECTS', 'false')
    domain = os.getenv('DOMAIN', None)
    elastic_host = os.getenv('ELASTICHOST', 'elastic-meta-service.default.svc')
    elastic_indexname = os.getenv('ELASTICINDEX', 'meta-index')
    kibana_host = os.getenv('KIBANAHOST', 'kibana-service.meta.svc')
    kibana_dashboard_file = os.getenv('KIBANADASHBOARD', '/dashboards/kibana-dashboard.json')
    kibana_port = os.getenv('KIBANAPORT', '5601')
    if domain is None:
        print("DOMAIN env not set -> exiting..")
        exit(1)
    kbn_xsrf = {'kbn-version': stack_version}

    if init_elastic:
        print("Initializing Elasticsearch-idices...")
        elastic_port = os.getenv('ELASTICPORT', '9200')
        recreate_index(index_name=elastic_indexname,
                       elastic_host=elastic_host, elastic_port=elastic_port)
        print("done.")

    if init_kibana:
        print("Initializing Kibana-Dashboards...")
        setup_kibana(kibana_dashboard=kibana_dashboard_file, kibana_host=kibana_host, kibana_port=kibana_port)
        create_index_pattern(kibana_host, kibana_port)
        print("done.")

    print("All done - End of init-container.")
