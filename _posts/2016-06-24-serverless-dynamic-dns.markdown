---
layout: post
title: Architecting Serverless Dynamic DNS Using AWS Services
date: '2016-06-24 16:52'
icon: sitemap
categories:
  - AWS
  - Python
weather_temp: 86
weather_cond: day-cloudy
---

The inspiration for this post and much of its content comes from [https://medium.com/aws-activate-startup-blog/building-a-serverless-dynamic-dns-system-with-aws-a32256f0a1d8#.6tzj1o286]().

**Problem**

You've recently set up a server at your home. You don't quite feel comfortable hosting it in a service like AWS or you happened to have a machine lying around you want to try and get some use out of. You've gotten it up and running and forwarded incoming traffic from your router to be forwarded to the server. You set up the DNS and are happy with the results.

Several weeks go by and you're at work. The weather is bad and you find out power was interrupted at your home. You are worried about the server (You didn't use a surge protector or a UPS, did you?) and decide to try and connect. As you fear you can't you go about your work and head home at the end of the day. The weather is clear and you arrive home to find the power is on. You try to connect to your server and everything is fine. You work into the evening and go to bed.

The next day at work you are trying to connect to your server again and find you can't. You try everything but nothing works. You get home and find you can connect fine. You decide to check the external IP address has changed. You call your ISP and find out that they issue dynamic addresses to residential customers and either won't give you a static one or are going to charge you far too much for one.

**Solution**

![Dynamic DNS in AWS](https://raw.githubusercontent.com/joshua-hull/joshua-hull.github.io/master/static/img/_posts/aws-dynamic-dns.png)

After some research you develop a plan to use [AWS API Gateway]([https://aws.amazon.com/api-gateway/]) and [AWS Lamda](https://aws.amazon.com/lambda). You plan on having a single API endpoint with two modes, `get` and `set`. The `get` method will simply return the IP address of whoever called the API. An example of calling the endpoint in the `get` mode is as follows:

{% highlight bash %}

wget https://....amazonaws.com/prod?mode=get

{% endhighlight %}

The return value for the call will be the following:

{% highlight javascript %}

{
  “return_message”: “176.32.100.36”,
  “return_status”: “success”
}

{% endhighlight %}

The client can then use this information to calculate a secure SHA256 hash of the information it needs to pass to the API in the `set` mode. This hash will consist of `IP_AddressHost_NameShared_Secret`. If the client wants to update the IP address for `host1.dyn.example.com` to `192.168.0.1` with the shared secret of `P@ssw0rd` then it would pass `SHA256(192.168.0.1host1.dyn.example.comP@ssw0rd)` in the `set` as show below:

{% highlight bash %}

HASH=`echo -n 192.168.0.1host1.dyn.example.comP@ssw0rd | shasum -a 256`

wget https://....amazonaws.com/prod?mode=set&hostname=host1.dyn.example.com&hash=$HASH

{% endhighlight %}

If the hostname does not need to be updated the following will be the return value:

{% highlight javascript %}

{
  “return_message”: “Your IP address matches the current Route53 DNS record.”,
  “return_status”: “success”
}

{% endhighlight %}

If the hostname is updated then the following will be the return value:

{% highlight javascript %}

{
  “return_message”: “Your hostname record host1.dyn.example.com. has been set to 176.32.100.36”,
  “return_status”: “success”
}

{% endhighlight %}


You setup the API inside of AWS and configure it to use Lamda as the backend. You create a single Lamda function to use and after some trial and error have the following result:

{% highlight python %}

from __future__ import print_function

import json
import re
import hashlib
import boto3

config_s3_region = 'us-west-2'
config_s3_bucket = 'my_bucket_name'
config_s3_key = 'config.json'

def read_s3_config():
    s3_client = boto3.client(
        's3',
        config_s3_region,
    )

    s3_client.download_file(
        config_s3_bucket,
        config_s3_key,
        '/tmp/%s' % config_s3_key
    )

    full_config = (open('/tmp/%s' % config_s3_key).read())
    return json.loads(full_config)

def route53_client(
  execution_mode,
  aws_region,
  route_53_zone_id,
  route_53_record_name,
  route_53_record_ttl,
  route_53_record_type,
  public_ip
  ):

    route53_client = boto3.client(
        'route53',
        region_name=aws_region
    )

    if execution_mode == 'get_record':
        current_route53_record_set = route53_client.list_resource_record_sets(
            HostedZoneId=route_53_zone_id,
            StartRecordName=route_53_record_name,
            StartRecordType=route_53_record_type,
            MaxItems='2'
        )

        for eachRecord in current_route53_record_set['ResourceRecordSets']:
            if eachRecord['Name'] == route_53_record_name:
                if len(eachRecord['ResourceRecords']) == 1:
                    for eachSubRecord in eachRecord['ResourceRecords']:
                        currentroute53_ip = eachSubRecord['Value']
                        return_status = 'success'
                        return_message = currentroute53_ip
                        return {'return_status': return_status,
                                'return_message': return_message}
                elif len(eachRecord['ResourceRecords']) > 1:
                    return_status = 'fail'
                    return_message = 'You should only have a single value for'\
                    ' your dynamic record.  You currently have more than one.'
                    return {'return_status': return_status,
                            'return_message': return_message}

    if execution_mode == 'set_record':
        change_route53_record_set = route53_client.change_resource_record_sets(
            HostedZoneId=route_53_zone_id,
            ChangeBatch={
                'Changes': [
                    {
                        'Action': 'UPSERT',
                        'ResourceRecordSet': {
                            'Name': route_53_record_name,
                            'Type': route_53_record_type,
                            'TTL': route_53_record_ttl,
                            'ResourceRecords': [
                                {
                                    'Value': public_ip
                                }
                            ]
                        }
                    }
                ]
            }
        )
        return 1

def run_set_mode(set_hostname, validation_hash, source_ip):
    try:
        full_config = read_s3_config()
    except:
        return_status = 'fail'
        return_message = 'There was an issue finding '\
            'or reading the S3 config file.'
        return {'return_status': return_status,
                'return_message': return_message}

    record_config_set = full_config[set_hostname]
    aws_region = record_config_set['aws_region']
    route_53_zone_id = record_config_set['route_53_zone_id']
    route_53_record_ttl = record_config_set['route_53_record_ttl']
    route_53_record_type = record_config_set['route_53_record_type']
    shared_secret = record_config_set['shared_secret']

    if not re.match(r'[0-9a-fA-F]{64}', validation_hash):
        return_status = 'fail'
        return_message = 'You must pass a valid sha256 hash in the '\
            'hash= argument.'
        return {'return_status': return_status,
                'return_message': return_message}


    calculated_hash = hashlib.sha256(source_ip + set_hostname + shared_secret).hexdigest()

    if not calculated_hash == validation_hash:
        return_status = 'fail'
        return_message = 'Validation hashes do not match.'
        return {'return_status': return_status,
                'return_message': return_message}
    else:
        route53_get_response = route53_client(
            'get_record',
            aws_region,
            route_53_zone_id,
            set_hostname,
            route_53_record_ttl,
            route_53_record_type,
            '')

        if not route53_get_response:
            route53_ip = '0'
        elif route53_get_response['return_status'] == 'fail':
            return_status = route53_get_response['return_status']
            return_message = route53_get_response['return_message']
            return {'return_status': return_status,
                    'return_message': return_message}
        else:
            route53_ip = route53_get_response['return_message']

        if route53_ip == source_ip:
            return_status = 'success'
            return_message = 'Your IP address matches '\
                'the current Route53 DNS record.'
            return {'return_status': return_status,
                    'return_message': return_message}
        else:
            return_status = route53_client(
                'set_record',
                aws_region,
                route_53_zone_id,
                set_hostname,
                route_53_record_ttl,
                route_53_record_type,
                source_ip)
            return_status = 'success'
            return_message = 'Your hostname record ' + set_hostname +\
                ' has been set to ' + source_ip
            return {'return_status': return_status,
                    'return_message': return_message}

def lambda_handler(event, context):

    execution_mode = event['execution_mode']
    source_ip = event['source_ip']
    query_string = event['query_string']
    validation_hash = event['validation_hash']
    set_hostname = event['set_hostname']

    execution_modes = ('set', 'get')
    if execution_mode not in execution_modes:
        return_status = 'fail'
        return_message = 'You must pass mode=get or mode=set arguments.'
        return_dict = {'return_status': return_status,
                       'return_message': return_message}

    if execution_mode == 'get':
        return_status = 'success'
        return_message = source_ip
        return_dict = {'return_status': return_status,
                       'return_message': return_message}
    else:
        return_dict = run_set_mode(set_hostname, validation_hash, source_ip)

    return return_dict

{% endhighlight %}

An example of the configuration file stored in S3 is as follows:

{% highlight javascript %}

{
    "host1.dyn.example.com.": {
        "aws_region": "us-west-2",
        "route_53_zone_id": "MY_ZONE_ID",
        "route_53_record_ttl": 60,
        "route_53_record_type": "A",
        "shared_secret": "SHARED_SECRET_1"
    },
    "host2.dyn.example.com.": {
        "aws_region": "us-west-2",
        "route_53_zone_id": "MY_ZONE_ID",
        "route_53_record_ttl": 60,
        "route_53_record_type": "A",
        "shared_secret": "SHARED_SECRET_2"
    }
}

{% endhighlight %}

An example of a `bash`-based client which can be set up as a `cron` job is as follows:

{% highlight bash %}

#!/bin/bash

#./dynamic_dns_lambda_client.sh host1.dyn.example.com. SHARED_SECRET_1 "abc123.execute-api.us-west-2.amazonaws.com/prod"

if [ $# -eq 0 ]
    then
    echo "Usage: $0 host1.dyn.example.com. sharedsecret \"abc123.execute-api.us-west-2.amazonaws.com/prod\""
    exit
fi

myHostname=$1
mySharedSecret=$2
myAPIURL=$3

myIP=`curl -q -s  "https://$myAPIURL?mode=get" | egrep -o '[0-9\.]+'`
myHash=`echo -n $myIP$myHostname$mySharedSecret | shasum -a 256 | awk '{print $1}'`

curl -q -s "https://$myAPIURL?mode=set&hostname=$myHostname&hash=$myHash"
echo

{% endhighlight %}
