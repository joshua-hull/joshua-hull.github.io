---
layout: "post"
title: "Developing Visualization for Security Groups"
date: 2017-03-29T13:02:32-04:00
icon: cloud
categories:
  - AWS
  - Python
weather_temp: 75
weather_cond: day-sunny
---

I was working on a task yesterday and throught I would write it up so that others could possibly benefit from it. I was working to document our AWS enviornment, specifically the security groups around each instance and how the instances are connected to each other and the internet as a whole.

I had been asked several weeks ago if there was some documentation of the AWS environment at work and how instances were interconnected. I didn't have any documentation at the time and it wasn't a huge deal so I let the topic drop. The other day however I was thinking about documenting AWS and that conversion came back into my head. I realized that with the AWS API you could generate the graph of the connections realtivly easily. Since everyone loves pretty pictures I wanted to see if I could visualize it as well.

The first step was to generate the graph of the security groups. This was another chance to use boto3<sup>[1](#footnote1)</sup>, the de-facto Python binding for the AWS API. After toying around I had the code that could generate the graph between each instance and the IPs that were allowed inbound access.

{% highlight python %}

import boto3
import json

def searchIpAddress(ipAddress):
    inputAddress = ipAddress.split('/')[0]
    returnString = ipAddress

    ec2 = boto3.resource('ec2')
    for instance in ec2.instances.all():
        for interface in instance.network_interfaces_attribute:
             if interface['PrivateIpAddress'] == inputAddress:
                 returnString = instance.instance_id
             if 'Association' in interface:
                if interface['Association']['PublicIp'] == inputAddress:
                    returnString = instance.instance_id
    return returnString

ec2 = boto3.resource('ec2')

graph = {}
cache = {}

for instance in ec2.instances.all():
    graph[instance.instance_id] = {}
    for interface in instance.network_interfaces_attribute:
        for group in interface['Groups']:
            security_group = ec2.SecurityGroup(group['GroupId'])
            for permission in security_group.ip_permissions:
                for IP in permission['IpRanges']:
                    if IP['CidrIp'] not in cache.keys():
                        cache[IP['CidrIp']] = searchIpAddress(IP['CidrIp'])
                    source = cache[IP['CidrIp']]
                    if IP['CidrIp'] in graph[instance.instance_id].keys():
                        graph[instance.instance_id][source] = graph[instance.instance_id][source] + 1
                    else:
                        graph[instance.instance_id][source] = 1

nodes = []
links = []

for node in graph:
    nodes.append({'id': node, 'group': 1})
    for edge in graph[node]:
        group = 2
        if edge.split('-')[0] == 'i':
            group = 1
        nodes.append({'id': edge, 'group': group})
        links.append({"source": edge, "target": node, "value": graph[node][edge]})

seen_nodes = set()
nodes_dedup = []
for obj in nodes:
    if obj['id'] not in seen_nodes:
        nodes_dedup.append(obj)
        seen_nodes.add(obj['id'])

data = {'nodes': nodes_dedup, 'links': links}

print(json.dumps(data))

{% endhighlight %}

There's one aspect of the code that I want to specifically call out. The method ```searchIpAddress``` searches for the instance ID for an IP address. This way if a security group refrences another instance the graph can properly know that. If we were to do this blindly though we would be pulling the list of instances from the API for each IP address for each port. Since we don't want to be wasteful we cache the results and preform a lookup in the cache and only call the method if we've not encountered that IP address before.

Now that we have the graph we need a way to visualize it. Here I wanted to use a Directed Graph<sup>[2](#footnote2)</sup> from D3<sup>[3](#footnote3)</sup>, the JavaScript visualization library. The python code above will output the graph in a way that can be used by D3. While I was able to get the graph working correctly I felt like the visualization was lacking. The graph couldn't handle the fact that the secutiy groups would have multiple ports vert well. It also couldn't handle the structure of our network very well but that was certainly no fault of the graph.

Overall I'm happy with the exercise. While the visualization aspect didn't turn out how I hoped I was able to get the data and have a way to reproduce it in the future should anyone need it. I hope to incorporate RDS as well in the future but that presents a different set of challenges.

If you've got questions about Amazon Web Services<sup>[4](#footnote4)</sup> or cloud technology in general feel free to contact me and I'll see how I can help bring my experience to the problem.

### Footnotes

* <a name="footnote1">1</a>:[https://boto3.readthedocs.io/en/latest/](https://boto3.readthedocs.io/en/latest/)
* <a name="footnote2">2</a>:[https://bl.ocks.org/mbostock/4062045](https://bl.ocks.org/mbostock/4062045)
* <a name="footnote3">3</a>:[https://d3js.org/](https://d3js.org/)
* <a name="footnote4">4</a>:[https://aws.amazon.com/](https://aws.amazon.com/)
