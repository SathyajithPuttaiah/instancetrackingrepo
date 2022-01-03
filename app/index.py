

import http.client
import urllib.parse
import json
import os
import time

from instance_parser import instance_parser

def send_response(request, response, status=None, reason=None):
    if status is not None:
        response['Status'] = status
    if reason is not None:
        response['Reason'] = reason
    if 'ResponseURL' in request and request['ResponseURL']:
        try:
            url = urllib.parse.urlparse(request['ResponseURL'])
            body = json.dumps(response)
            https = http.client.HTTPSConnection(url.hostname)
            https.request('PUT', url.path + '?' + url.query, body)
        except:
            print("Failed to send the response to the provided URL")
    return response


def handler(event, context):

    try:
        
        print('received event:',event)
        #time.sleep(60)
        response = {}
        
        if ('ServiceToken' in event):            
            response['Status'] = 'SUCCESS'
            response['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name
            response['PhysicalResourceId'] = context.log_stream_name
            response['StackId'] = event['StackId']
            response['RequestId'] = event['RequestId']
            response['LogicalResourceId'] = event['LogicalResourceId']
            response['NoEcho'] = False        
        if('RequestType' in event):
            # Create and Update of stack - Send the response to CF
            if (event['RequestType'] in ['Create','Update']) and ('ServiceToken' in event):

                AWS_Account = context.invoked_function_arn.split(":")[4]
                AWS_Region = context.invoked_function_arn.split(":")[3]

                input_args = {}
                input_args['bucket']= os.environ['backupBucket']
                input_args['folder']  = 'running-instances'
                input_args['AWSAccount']  = AWS_Account
                input_args['AWSRegion']  = AWS_Region
                input_args['sns_topic'] = os.environ['sns_topic']

                instance_parser_obj = instance_parser(**input_args)
                instance_parser_obj.exec_instance_parser()

                send_response(event, response, status='SUCCESS', reason='Lambda Invoked')

            # Delete of Stack - Only send the response to CF after deleting the parameters
            if (event['RequestType'] in ['Delete']) and ('ServiceToken' in event):
                send_response(event, response, status='SUCCESS', reason='Delete event received')


        return {
            'statusCode': 200
        }
    except Exception as e:
        print('Error - Index.py file',str(e))
        send_response(event, response, status='SUCCESS', reason='Delete event received')