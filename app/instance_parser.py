import json
import boto3
import os
import datetime 
import time

from botocore.config import Config

class instance_parser():
    def __init__(self,**input_args):

        config=Config(retries=dict(max_attempts=10,mode='standard'))

        self.ec2_resource = boto3.resource('ec2',config=config)
        self.s3_client_obj = boto3.client('s3',config=config)
        self.sns_client_obj = boto3.client('sns',config=config)

        self.bucket_name = input_args['bucket']
        self.folder = input_args['folder']
        self.AWSAccount = input_args['AWSAccount']
        self.AWSRegion = input_args['AWSRegion']
        self.sns_topic = input_args['sns_topic']
        self.message = """All, \n
List of all running ec2 instance in account: %s, region: %s information can be found in s3 bucket : %s/%s \n
Thanks,
Team""" % (self.AWSAccount,self.AWSRegion,self.bucket_name,self.folder) 
        self.subject = "Lambda Function Completed- Listing all ec2 instances" 

# method will list out all the instances and tracks as a list
# making use of next token, if these are multiple page while rendering the ec2 list
    def get_instances_info(self):
        
        try:
            print('List all the instances')
            
            # Get information for all the instances 
            # Listing only those instances whose 'owner' is 'ABCD'
            extra_args = {}
            #['running', 'pending','stopping','stopped']
            extra_args['Filters'] = [
                                    {'Name':'tag:Owner', 'Values':['ABCD']},
                                    {'Name': 'instance-state-name', 'Values': ['running','pending']}
                                    ]
            instances_list = []
            while(True):
                
                all_instances = self.ec2_resource.instances.filter(**extra_args)
                for instance in all_instances:
                    ec2info = {}
                    ec2info[instance.id]  = {
                            'Type': instance.instance_type, 
                            'State': instance.state['Name'], 
                            'Public IP': instance.public_ip_address
                        }
                
                    print('instance info is fetched for {} and ec2info:{}'.format(instance.id,ec2info))

                    s3_input_args = {}
                    s3_input_args['ec2_info'] = ec2info
                    s3_input_args['instance_id'] = instance.id
                    instances_list.append(s3_input_args)
                if ('NextToken' in all_instances):
                    extra_args['NextToken'] = all_instances['NextToken']
                else:
                    break
            return instances_list

        except Exception as e:
            print('error in process_instances():',e)

# logs all the instances to s3 bucket
# a separate file will be created for each instances and body will contain the details
    def create_s3_file(self,s3_input_args):
        try:
            print('inside create s3:',s3_input_args)
            ec2info = s3_input_args['ec2_info']
            instanceid = s3_input_args['instance_id']
            filename = instanceid +'.json'

            s3path = self.folder+"/" + filename

            data_file = open('/tmp/'+filename, 'w+')
            data_file.write(str(dict(ec2info.items())))
            #data_file.write(str(dict(s3_input_args)))
            data_file.close()   

            self.s3_client_obj.upload_file('/tmp/'+filename, self.bucket_name , s3path)
            print('Upload complete')

            return 'Upload Complete'

        except Exception as e:
            print('error in create_s3_file():',e)
            raise

# will be called to send out a notification to user
# user must have subscried to the SNS topic.
    def sns_publish(self, sns_topic):
        try:
            
            #Send notification     
            self.sns_client_obj.publish(TopicArn=sns_topic, Message=self.message, Subject=self.subject) 
            print('Notification sent')
        except Exception as e:
            print('error in sns_publish():',e)
            raise

    def exec_instance_parser(self):
        instances_list = self.get_instances_info()
        print('instances_list:',instances_list)
        [*map(self.create_s3_file, instances_list)]
        self.sns_publish(self.sns_topic)

        return {
            'statusCode': 200,
            'body': json.dumps('Lambda Executed successfully!')
        }