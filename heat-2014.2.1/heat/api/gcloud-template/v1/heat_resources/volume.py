volumeResource = \
{
    "parameters": {
        "vol_size": {
            "type": "number",
            "description": "size  of  vol"
        },
        "volume_type": {
            "type": "string",
            "description": "type of volume"
        },
        "volume_pool":{
            "type": "string",
            "description": "name of volume pool"
        }
    },
    "resources": {
        "server_vol": {
            "type": "OS::Cinder::GcloudVolume",
            "properties": {
                "size": {
                    "get_param": "vol_size"
                },
                "volume_type": {
                    "get_param": "volume_type"
                },
                "pool_name": {
                    "get_param": "volume_pool"
                },
                "host_name": {
                    "get_attr": [
                        "gcloud-vm",
                        "host_name"
                    ]
                }
            }
        },
        "vol_attach": {
            "type": "OS::Cinder::GcloudVolumeAttachment",
            "properties": {
                "instance_id": {
                    "get_attr": [
                        "gcloud-vm",
                        "instaceId"
                    ]
                },
                 "volume_id": {
                 "get_resource": "server_vol"
                  },
            }

        }
    }
}
