#!/usr/bin/env python3
"""Print a default-VPC subnet whose availability zone offers an instance type.

Usage: aws_pick_subnet.py <region> <instance-type>
Prints JSON {"vpc_id", "subnet_id", "zone"} or {"error"}; exits 0 either way so the
caller can report the reason. Credentials come from the AWS_* environment.
"""
import json
import sys

import boto3


def pick(region, instance_type):
    ec2 = boto3.client("ec2", region_name=region)
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"]
    if not vpcs:
        return {"error": f"the AWS region {region} has no default VPC"}
    vpc_id = vpcs[0]["VpcId"]
    offered = set()
    paginator = ec2.get_paginator("describe_instance_type_offerings")
    for page in paginator.paginate(
        LocationType="availability-zone",
        Filters=[{"Name": "instance-type", "Values": [instance_type]}],
    ):
        offered.update(o["Location"] for o in page["InstanceTypeOfferings"])
    if not offered:
        return {"error": f"AWS doesn't offer {instance_type} in {region}"}
    subnets = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc_id]}])["Subnets"]
    usable = sorted(
        (s for s in subnets if s["AvailabilityZone"] in offered and s.get("MapPublicIpOnLaunch", False)),
        key=lambda s: s["AvailabilityZone"],
    ) or sorted((s for s in subnets if s["AvailabilityZone"] in offered), key=lambda s: s["AvailabilityZone"])
    if not usable:
        return {"error": f"AWS doesn't offer {instance_type} in any zone of the default VPC in {region}"}
    return {"vpc_id": vpc_id, "subnet_id": usable[0]["SubnetId"], "zone": usable[0]["AvailabilityZone"]}


if __name__ == "__main__":
    try:
        result = pick(sys.argv[1], sys.argv[2])
    except Exception as e:  # noqa: BLE001 - the caller reports any failure as text
        result = {"error": f"{type(e).__name__}: {e}"}
    print(json.dumps(result))
