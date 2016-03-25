from heat.common import exception
from heat.engine import attributes
from heat.engine import constraints
from heat.engine import properties
from heat.engine import resource
from heat.openstack.common import log as logging
from heat.common.i18n import _
from client import ComputeClient
from client import VolumeClient
from heat.engine import support
from heat.common import short_id
LOG = logging.getLogger(__name__)

class GcloudVolumeAttachment(resource.Resource):
    PROPERTIES = (
        INSTANCE_ID, VOLUME_ID,
    ) = (
        'instance_id', 'volume_id',
    )

    properties_schema = {
        INSTANCE_ID: properties.Schema(
            properties.Schema.STRING,
            _('The ID of the server to which the volume attaches.'),
            required=True,
            update_allowed=True
        ),
        VOLUME_ID: properties.Schema(
            properties.Schema.STRING,
            _('The ID of the volume to be attached.'),
            required=True,
            update_allowed=True
        ),

    }
    def __init__(self, name, json_snippet, stack):
        self.client = ComputeClient(stack.context)
        super(GcloudVolumeAttachment, self).__init__(name, json_snippet, stack)

    def handle_create(self):
        LOG.debug(_("attach volume start"))
        return self.client.attach_volume(self.properties[self.INSTANCE_ID],self.properties[self.VOLUME_ID])

    def check_create_complete(self, info):
        response = self.client.list_volume(self.properties[self.INSTANCE_ID])
        data = response.get("data", None)
        if data is not None:
            for elememt in data:
                if elememt.get("volumeId", None) == self.properties[self.VOLUME_ID] and \
                                elememt.get("instanceId", None) == self.properties[self.INSTANCE_ID]:
                    return True

            return False
        else:
            raise exception.ClientRequestException(text="gcompute_list_volume")

    def handle_delete(self):
        LOG.debug(_("detach_volume volume start"))
        return self.client.detach_volume(self.properties[self.INSTANCE_ID],self.properties[self.VOLUME_ID])


    def check_delete_complete(self, info):
        response = self.client.list_volume(self.properties[self.INSTANCE_ID])
        data = response.get("data", None)
        if data is not None:
            for elememt in data:
                if elememt.get("volumeId", None) == self.properties[self.VOLUME_ID] and \
                                elememt.get("instanceId", None) == self.properties[self.INSTANCE_ID]:
                    return False

            return True
        else:
            raise exception.ClientRequestException(text="gcompute_list_volume")



class CinderVolume(resource.Resource):

    PROPERTIES = (
        AVAILABILITY_ZONE, SIZE, SNAPSHOT_ID, BACKUP_ID, NAME,
        DESCRIPTION, VOLUME_TYPE, METADATA, IMAGE_REF, IMAGE,
        SOURCE_VOLID, HOST_NAME, POOL_NAME
    ) = (
        'availability_zone', 'size', 'snapshot_id', 'backup_id', 'name',
        'description', 'volume_type', 'metadata', 'imageRef', 'image',
        'source_volid', 'host_name', 'pool_name'
    )

    ATTRIBUTES = (
        AVAILABILITY_ZONE_ATTR, SIZE_ATTR, SNAPSHOT_ID_ATTR, DISPLAY_NAME,
        DISPLAY_DESCRIPTION, VOLUME_TYPE_ATTR, METADATA_ATTR,
        SOURCE_VOLID_ATTR, STATUS, CREATED_AT, BOOTABLE, METADATA_VALUES_ATTR,
    ) = (
        'availability_zone', 'size', 'snapshot_id', 'display_name',
        'display_description', 'volume_type', 'metadata',
        'source_volid', 'status', 'created_at', 'bootable', 'metadata_values',
    )

    properties_schema = {
        AVAILABILITY_ZONE: properties.Schema(
            properties.Schema.STRING,
            _('The availability zone in which the volume will be created.')
        ),
        SIZE: properties.Schema(
            properties.Schema.INTEGER,
            _('The size of the volume in GB. '
              'On update only increase in size is supported.'),
            update_allowed=True,
            constraints=[
                constraints.Range(min=1),
            ]
        ),
        SNAPSHOT_ID: properties.Schema(
            properties.Schema.STRING,
            _('If specified, the snapshot to create the volume from.')
        ),
        BACKUP_ID: properties.Schema(
            properties.Schema.STRING,
            _('If specified, the backup to create the volume from.')
        ),
        NAME: properties.Schema(
            properties.Schema.STRING,
            _('A name used to distinguish the volume.'),
            update_allowed=True,
        ),
        DESCRIPTION: properties.Schema(
            properties.Schema.STRING,
            _('A description of the volume.'),
            update_allowed=True,
        ),
        VOLUME_TYPE: properties.Schema(
            properties.Schema.STRING,
            _('If specified, the type of volume to use, mapping to a '
              'specific backend.')
        ),
        METADATA: properties.Schema(
            properties.Schema.MAP,
            _('Key/value pairs to associate with the volume.'),
            update_allowed=True,
        ),
        IMAGE_REF: properties.Schema(
            properties.Schema.STRING,
            _('The ID of the image to create the volume from.'),
            support_status=support.SupportStatus(
                support.DEPRECATED,
                _('Use property %s.') % IMAGE)
        ),
        IMAGE: properties.Schema(
            properties.Schema.STRING,
            _('If specified, the name or ID of the image to create the '
              'volume from.'),
            constraints=[
                constraints.CustomConstraint('glance.image')
            ]
        ),
        SOURCE_VOLID: properties.Schema(
            properties.Schema.STRING,
            _('If specified, the volume to use as source.')
        ),
        # add by zyk
        HOST_NAME: properties.Schema(
          properties.Schema.STRING,
          _("just for local volum"),
          default="localhost",
          update_allowed=False
        ),
        # add by zyk
        POOL_NAME: properties.Schema(
          properties.Schema.STRING,
          _("pool of storage"),
          default=None,
          update_allowed=False
        ),
    }

    def _format_properpy(self, name):
        format_dit = {
            "RBD": "distributed",
            "Central": "central",
            "Local": "local"
        }
        return format_dit.get(name, None)

    def __init__(self, name, json_snippet, stack):
        self.client = VolumeClient(stack.context)
        super(CinderVolume, self).__init__(name, json_snippet, stack)

    def _display_description(self):
        return self.properties[self.DESCRIPTION]

    def _create_porperties(self):
        if self.properties[self.POOL_NAME] == "auto":
            properties = {
                'size': self.properties[self.SIZE],
                "volume_type":  self._format_properpy(self.properties[self.VOLUME_TYPE]),
            }
        else:
            properties = {
                'size': self.properties[self.SIZE],
                'pool_name': self.properties[self.POOL_NAME],
                 "volume_type": self._format_properpy(self.properties[self.VOLUME_TYPE]),
            }
        if self.properties[self.VOLUME_TYPE] == "Local":
            properties['host_id'] = self.properties[self.HOST_NAME]
        properties['name'] =  short_id.generate_id()
        properties['createmethod'] = "create"
        properties['count'] = 1

        return properties





    def handle_create(self):
        """
        backup_id = self.properties.get(self.BACKUP_ID)
        cinder = self.cinder()
        if backup_id is not None:
            vol_id = cinder.restores.restore(backup_id).volume_id

            vol = cinder.volumes.get(vol_id)
            vol.update(
                name=self._display_name(), # display_name=self._display_name()
                description=self._display_description()) # display_description=self._display_description())
        else:
            vol = cinder.volumes.create(
                name=self._display_name(), #display_name=self._display_name(),
                description=self._display_description(), #display_description=self._display_description(),
                **self._create_arguments())
        self.resource_id_set(vol.id)

        return vol
        """
        try:
            response = self.client.create(self._create_porperties())
            if response['success']:
                self.resource_id_set(response.get('data',None)[0]['id'])
                return response.get('data',None)[0]['id']
            else:
                raise Exception("create volume error")
        except Exception, e:
            #heat_server_task_00008
            self.stack.error_codes.append('heat_server_task_00008')
            raise e

    def handle_delete(self):
        try:
            if self.resource_id is None:
                return 0
            response = self.client.delete(self.resource_id)
            if response['success'] == False:
                raise Exception("delete volume error")
            else:
                return self.resource_id
        except Exception, e:
            self.stack.error_codes.append('heat_server_task_00009')
            raise e

    def check_create_complete(self, vol):
        try:  #available
            response = self.client.detail(self.resource_id)
            if response['success']:
                if response["data"]['status'] == "available":
                    return True
                else:
                    return False
            else:
                raise Exception("create volume error")
        except Exception, e:
            #heat_server_task_00008
            self.stack.error_codes.append('heat_server_task_00008')
            raise e


    def check_delete_complete(self, vol):
        try:
            if self.resource_id is None:
                return True
            response = self.client.detail(self.resource_id)
            if response['success']: # in-use trashed
                if response["data"]['status'] == "in-use":
                    raise Exception("volume in use")
                elif response["data"]['status'] == "trashed":
                    return True
                else:
                    return False
            else:
                raise Exception("delete volume error")
        except Exception, e:
            #heat_server_task_00008
            self.stack.error_codes.append('heat_server_task_00008')
            raise e



def resource_mapping():
    return {

        'OS::Cinder::GcloudVolumeAttachment': GcloudVolumeAttachment,
        'OS::Cinder::GcloudVolume': CinderVolume,
    }