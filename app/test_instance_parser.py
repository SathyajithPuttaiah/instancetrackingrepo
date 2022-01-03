import boto3, boto
import pytest
import os

from instance_parser import instance_parser
from moto import mock_s3, mock_ec2, mock_sns

from tempfile import NamedTemporaryFile

#Prepare the input args for the instance_parser class file
input_args = {}
input_args['bucket'] = 'test-bucket'
input_args['folder'] = 'test-folder'
input_args['AWSAccount'] = 'test-account'
input_args['AWSRegion'] = 'test-region'
input_args['sns_topic'] = 'test-sns'
instance_tags = [
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                        {
                            'Key': 'Owner',
                            'Value': 'ABCD'
                        }
                        ]

                    }
                ]
@mock_ec2
def test_get_instances_info():
    instance_count = 2
    conn = boto3.resource('ec2')
    conn.create_instances(ImageId = 'ami-12c6146b', MinCount=instance_count, MaxCount=instance_count,
                        TagSpecifications=instance_tags
                        )

    parser_obj = instance_parser(**input_args)
    instances = parser_obj.get_instances_info()
    assert len(instances) == instance_count

@mock_s3
def test_list_objects():
    with mock_ec2():
        instance_count = 2
        conn = boto3.resource('ec2')
        conn.create_instances(ImageId = 'ami-12c6146b', MinCount=instance_count, MaxCount=instance_count,  TagSpecifications=instance_tags)
        parser_obj = instance_parser(**input_args)
        instances = parser_obj.get_instances_info()
        expected_result = input_args['folder'] + '/'+  instances[0]['instance_id'] + '.json'

    s3_client = boto3.client('s3', region_name='us-east-1')
    s3_client.create_bucket(Bucket=input_args['bucket'])
    parser_obj = instance_parser(**input_args)
    parser_obj.create_s3_file(instances[0])    
    objects = s3_client.list_objects(Bucket=input_args['bucket'])
    actual_result = objects['Contents'][0]['Key']
    assert expected_result == actual_result     

@mock_sns
def test_sns_publish():
    conn = boto3.client('sns')

    response = conn.create_topic(Name = input_args['sns_topic'])
    parser_obj = instance_parser(**input_args)
    parser_obj.sns_publish(response['TopicArn'])

# Call the test methods here
""" if __name__ == "__main__":
    # test_get_instances_info()
    #test_list_objects()
    test_sns_publish() """