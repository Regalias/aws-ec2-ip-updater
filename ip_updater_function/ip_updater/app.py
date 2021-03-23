import boto3
from botocore.exceptions import ClientError
import os

ec2 = boto3.client('ec2')
r53 = boto3.client('route53')
hosted_zone_id = os.environ.get('HOSTED_ZONE_ID')
record_name = os.environ.get('RECORD_NAME')

def handler(event, context): 

    if hosted_zone_id is not None and record_name is not None:
        main(event)
    else:
        print("[ERROR] Missing hosted zone or record name configuration")

    return {'status': 'done'}

def main(event):
    instance_id = event.get('detail').get('instance-id')
    public_ip = get_instance_public_ip(instance_id)
    if public_ip is not None:
        update_route53_record(public_ip)
        print(f"[INFO] Updated ({hosted_zone_id}) {record_name} -> ({instance_id}) {public_ip}")

def get_instance_public_ip(instance_id):

    try:
        resp = ec2.describe_instances(InstanceIds=[instance_id])
    except ClientError as e:
        if e.response['Error']['Code'] == 'InvalidInstanceID.Malformed':
            print(f"[ERROR] Instance {instance_id} does not exist!")
        return None

    try:
        instance_public_ip = resp.get('Reservations')[0].get('Instances')[0].get('PublicIpAddress')
        if not instance_public_ip:
            print(f"[ERROR] Instance {instance_id} does not have a public IP address assigned!")
            return None
        else:
            return instance_public_ip

    except (KeyError,ValueError) as e:
        print(f"[ERROR] Instance {instance_id} didn't have expected properties!")
        return None

def update_route53_record(public_ip):
    r53.change_resource_record_sets(
        HostedZoneId=hosted_zone_id,
        ChangeBatch={
            'Comment': 'auto-update by EC2 IP updater lambda',
            'Changes': [
                {
                    'Action': 'UPSERT',
                    'ResourceRecordSet': {
                        'Name': record_name,
                        'Type': 'A',
                        'TTL': 60,
                        'ResourceRecords': [{'Value': public_ip}]
                    }
                }
            ]
        }
    )