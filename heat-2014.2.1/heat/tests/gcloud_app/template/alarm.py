cpu_util_alarm_resource =\
    {
    "heat_template_version": "2013-05-23",
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
                "matching_metadata": {
                        "metadata.user_metadata.stack": "1fe9fe22-e7e5-4fcf-bd6a-0eb9ffec9ea6"
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
                "period": 200,
                "evaluation_periods": 1,
                "threshold": {
                    "get_param": "cputil_threshold_low"
                },
                  "matching_metadata": {
                        "metadata.user_metadata.stack": "1fe9fe22-e7e5-4fcf-bd6a-0eb9ffec9ea6"
                 },
                "comparison_operator": "lt"
            }
        }
    }
}

request_body =  {
    "disable_rollback": True,
    "parameters": {
        "cputil_threshold_high": 80,
        "cputil_threshold_low": 20,

    },
    "stack_name": "test_create_alarm",
    "environment": {},
    "template": cpu_util_alarm_resource,
    "iscaler": True,
    "enduser_id": "8ad84e12-7dbb-4ce5-8755-b624056d8433",
    "description": "just for test",
    "app_name": "test_create_alarm"
}
