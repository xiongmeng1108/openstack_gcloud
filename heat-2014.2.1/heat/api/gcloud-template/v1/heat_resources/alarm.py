cpu_util_alarm_resource =\
    {
    "heat_template_version": "2013-05-23T00:00:00.000Z",
    "description": "elastic extension  template",
    "parameters": {
        "cputil_threshold_high": {
            "type": "number",
            "description": "cpu_low_threshold",
            "constraints": [
                {
                    "range": {
                        "min": 0,
                        "max": 100
                    }
                }
            ]
        },
        "cputil_threshold_low": {
            "type": "number",
            "description": "cpu_high_threshold",
            "constraints": [
                {
                    "range": {
                        "min": 0,
                        "max": 100
                    }
                }
            ]
        }
    },
    "resources": {
        "cputil_alarm_high": {
            "type": "OS::Ceilometer::Alarm",
            "properties": {
                "description": "Scale-up if the average cpu > {get_param: cputil_threshold_high} for 1 minute",
                "meter_name": "cpu_util",
                "statistic": "avg",
                "period": 60,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "cputil_threshold_high"
                },
                "alarm_actions": [
                    {
                        "get_attr": [
                            "web_server_scaleout_policy",
                            "alarm_url"
                        ]
                    }
                ],
                "matching_metadata": {
                    "metadata.user_metadata.stack": {
                        "get_param": "OS::stack_id"
                    }
                },
                "comparison_operator": "gt"
            }
        },
        "cputil_alarm_low": {
            "type": "OS::Ceilometer::Alarm",
            "properties": {
                "description": "Scale-down if the average CPU < {get_param: cputil_threshold_low}for 10 minutes",
                "meter_name": "cpu_util",
                "statistic": "avg",
                "period": 600,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "cputil_threshold_low"
                },
                "alarm_actions": [
                    {
                        "get_attr": [
                            "web_server_scaledown_policy",
                            "alarm_url"
                        ]
                    }
                ],
                "matching_metadata": {
                    "metadata.user_metadata.stack": {
                        "get_param": "OS::stack_id"
                    }
                },
                "comparison_operator": "lt"
            }
        }
    }
}




mem_util_resources =\
    {
    "heat_template_version": "2013-05-23T00:00:00.000Z",
    "description": "elastic extension  template",
    "parameters": {
        "memutil_threshold_high": {
            "type": "number",
            "description": "memutil_threshold_high",
            "constraints": [
                {
                    "range": {
                        "min": 0,
                        "max": 100
                    }
                }
            ]
        },
        "memutil_threshold_low": {
            "type": "number",
            "description": "memutil_threshold_low",
            "constraints": [
                {
                    "range": {
                        "min": 0,
                        "max": 100
                    }
                }
            ]
        }
    },
    "resources": {
        "memutil_alarm_high": {
            "type": "OS::Ceilometer::Alarm",
            "properties": {
                "description": "Scale-up if the average  memory > {get_param: memutil_threshold_high} for 1 minute",
                "meter_name": "mem_util",
                "statistic": "avg",
                "period": 60,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "memutil_threshold_high"
                },
                "alarm_actions": [
                    {
                        "get_attr": [
                            "web_server_scaleout_policy",
                            "alarm_url"
                        ]
                    }
                ],
                "matching_metadata": {
                    "metadata.user_metadata.stack": {
                        "get_param": "OS::stack_id"
                    }
                },
                "comparison_operator": "gt"
            }
        },
        "memutil_alarm_low": {
            "type": "OS::Ceilometer::Alarm",
            "properties": {
                "description": "Scale-down if memory < {get_param: memutil_threshold_low}for 10 minutes",
                "meter_name": "mem_util",
                "statistic": "avg",
                "period": 600,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "memutil_threshold_low"
                },
                "alarm_actions": [
                    {
                        "get_attr": [
                            "web_server_scaledown_policy",
                            "alarm_url"
                        ]
                    }
                ],
                "matching_metadata": {
                    "metadata.user_metadata.stack": {
                        "get_param": "OS::stack_id"
                    }
                },
                "comparison_operator": "lt"
            }
        }
    }
}


read_byte_alarm_resource =\
    {
    "heat_template_version": "2013-05-23T00:00:00.000Z",
    "description": "elastic extension  template",
    "parameters": {
        "read_bytes_high_threshold": {
            "type": "number",
            "description": "read_bytes_high_threshold unit B",
            "constraints": [
                {
                    "range": {
                        "min": 0,
                        "max": 1000000000
                    }
                }
            ]
        },
        "read_bytes_low_threshold": {
            "type": "number",
            "description": "read_bytes_low_threshold unit B",
            "constraints": [
                {
                    "range": {
                        "min": 0,
                        "max": 1000000000
                    }
                }
            ]
        }
    },
    "resources": {
        "read_bytes_alarm_high": {
            "type": "OS::Ceilometer::Alarm",
            "properties": {
                "description": "Scale-up if the average cpu > {get_param: read_bytes_high_threshold} for 1 minute",
                "meter_name": "disk.read.bytes.rate",
                "statistic": "avg",
                "period": 60,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "read_bytes_high_threshold"
                },
                "alarm_actions": [
                    {
                        "get_attr": [
                            "web_server_scaleout_policy",
                            "alarm_url"
                        ]
                    }
                ],
                "matching_metadata": {
                    "metadata.user_metadata.stack": {
                        "get_param": "OS::stack_id"
                    }
                },
                "comparison_operator": "gt"
            }
        },
        "read_bytes_alarm_low": {
            "type": "OS::Ceilometer::Alarm",
            "properties": {
                "description": "Scale-down if the average CPU < {get_param: read_bytes_low_threshold}for 10 minutes",
                "meter_name": "disk.read.bytes.rate",
                "statistic": "avg",
                "period": 600,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "read_bytes_low_threshold"
                },
                "alarm_actions": [
                    {
                        "get_attr": [
                            "web_server_scaledown_policy",
                            "alarm_url"
                        ]
                    }
                ],
                "matching_metadata": {
                    "metadata.user_metadata.stack": {
                        "get_param": "OS::stack_id"
                    }
                },
                "comparison_operator": "lt"
            }
        }
    }
}



write_byte_alarm_resource =\
    {
    "heat_template_version": "2013-05-23T00:00:00.000Z",
    "description": "elastic extension  template",
    "parameters": {
        "write_bytes_high_threshold": {
            "type": "number",
            "description": "write_bytes_high_threshold unit B",
            "constraints": [
                {
                    "range": {
                        "min": 0,
                        "max": 1000000000
                    }
                }
            ]
        },
        "write_bytes_low_threshold": {
            "type": "number",
            "description": "write_bytes_low_threshold unit B",
            "constraints": [
                {
                    "range": {
                        "min": 0,
                        "max": 1000000000
                    }
                }
            ]
        }
    },
    "resources": {
        "write_bytes_alarm_high": {
            "type": "OS::Ceilometer::Alarm",
            "properties": {
                "description": "Scale-up if the average write_bytes > {get_param: write_bytes_high_threshold} for 1 minute",
                "meter_name": "disk.writes.bytes.rate",
                "statistic": "avg",
                "period": 60,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "write_bytes_high_threshold"
                },
                "alarm_actions": [
                    {
                        "get_attr": [
                            "web_server_scaleout_policy",
                            "alarm_url"
                        ]
                    }
                ],
                "matching_metadata": {
                    "metadata.user_metadata.stack": {
                        "get_param": "OS::stack_id"
                    }
                },
                "comparison_operator": "gt"
            }
        },
        "write_bytes_alarm_low": {
            "type": "OS::Ceilometer::Alarm",
            "properties": {
                "description": "Scale-down if the average write_bytes <{get_param: write_bytes_low_threshold} for 1 minutes",
                "meter_name": "disk.write.bytes.rate",
                "statistic": "avg",
                "period": 60,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "write_bytes_low_threshold"
                },
                "alarm_actions": [
                    {
                        "get_attr": [
                            "web_server_scaledown_policy",
                            "alarm_url"
                        ]
                    }
                ],
                "matching_metadata": {
                    "metadata.user_metadata.stack": {
                        "get_param": "OS::stack_id"
                    }
                },
                "comparison_operator": "lt"
            }
        }
    }
}

map_alarm= {
    "cpu_util": cpu_util_alarm_resource.copy(),
    "mem_util": mem_util_resources.copy(),
    "disk_io_read": read_byte_alarm_resource.copy(),
    "disk_io_write": write_byte_alarm_resource.copy()
}