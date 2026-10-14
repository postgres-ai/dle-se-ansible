#!/usr/bin/env python3
"""Delete the EC2 key pairs tagged server=<name> (a deploy's leftover temporary keys).

Usage: aws_delete_server_keys.py <region> <server-name>
Prints the deleted key names, one per line. Credentials come from the AWS_* environment.
"""
import sys

import boto3

region, server = sys.argv[1], sys.argv[2]
ec2 = boto3.client("ec2", region_name=region)
for key in ec2.describe_key_pairs(Filters=[{"Name": "tag:server", "Values": [server]}])["KeyPairs"]:
    ec2.delete_key_pair(KeyPairId=key["KeyPairId"])
    print(key["KeyName"])
