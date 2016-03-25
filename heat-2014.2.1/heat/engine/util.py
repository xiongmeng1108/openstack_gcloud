__author__ = 'zhangyk'
import heat.rpc.client
from functools import wraps
from resources.gcloud import client

def report_task_status(handler):
    """
    Decorator for report task  status
    """
    @wraps(handler)
    def handler_report(stack, task_id , *args,  **kwargs):
        #cntx = {"name": "heat"}
        #report_client.report_stack_task(cntx, stack)
        #print "task_id is %s and status is %s" %(task_id)
        #info = handler(stack, **kwargs)
        #report_client.report_stack_task(cntx, stack)
        #return info
        if task_id:
            stack_id = stack.id
            print "start task_id is %s and status is %s" %(task_id, stack.status)
            info = handler(stack, *args, **kwargs)
            report_client = client.GcloudTaskStatusReport(stack.context)
            properties = {
                "object_id": stack_id,
                "task_id": task_id,
                "status": stack.status,

            }
            if stack.error_codes:
                print "error code: %s"  %stack.error_codes[0]
                properties['code'] = stack.error_codes[0]
            report_client.report_task_status(properties)
            print "end task_id is %s and status is %s" %(task_id, stack.status)
            return info
        else:
            return handler(stack, *args, **kwargs)

    return handler_report



