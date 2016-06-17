---
layout: post
title:  "AWS Security Groups and Dynamic IP Addresses"
date:   2016-06-10T09:48:12-04:00
categories: [AWS, Python, Terraform]
weather:
  - temp: 78
    cond: day-sunny
---
**Problem**

You are given the task to only allow access to certain AWS resources to the office you work in. You create a Security Group and ask a colleague for the external IP address range assigned to the office. He tells you that there is not static range. The office, along with the rest of the building, share a commercial ISP with dynamic addresses. In addition to that, there is not one but three IPSs that are load balanced for outgoing traffic. The external IP address of the machine you're working on can theoretically change on a per request basis.

**Solution**

You decide there's nothing you can do about the rest of the building being able to access the resources. It isn't a security threat if they can and there no obvious way that they would be able to find the resources. You decide you'll write a Python script that gets your public IP address. It will then calculate if that address is in the list of address ranges you already know about. If the address is in the range then everything is good. If the address isn't in the range then the script will calculate a new range so you can go update the Security Group.

After an hour or so you have the following script working:

{% highlight python %}

import urllib.request as urllib2
import re
from netaddr import *
import pprint

# Get our external network address and calculate a Class C CIDR based on it.
resource = urllib2.urlopen('http://ipinfo.io/ip')
ext_ip =  resource.read().decode(resource.headers.get_content_charset())
my_ip = re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",ext_ip).group()
my_cidr = IPNetwork(my_ip)
my_cidr.prefixlen = 24
my_cidr = my_cidr.cidr

print("IP Address: " + str(my_ip))
print("CIDR: " + str(my_cidr))


# The list of existing CIDR ranges
lines = []
ip_list = []
with open('Desktop/AWS/IPs.txt') as infile:
    for line in infile:
        ip_list.append(IPNetwork(line))
        lines.append(line)

# Find the largest ranges that cover our CIDR ranges.
ip_merged = cidr_merge(ip_list)

# Try to find if we are in an existing CIDR by looking at the first address in
# the range.
in_range = False
for network in ip_merged:
    if my_cidr[0] == network[0]:
        in_range = True
        print("Possible match: " + str(network))
        pass
    pass

if in_range:
    print("We should be in the existing range:")
    pass
else:
    print("We might not be in the existing range. Proposed new range:")
    ip_list.append(my_cidr)
    ip_merged = cidr_merge(ip_list)
    pass

lines = []
for network in ip_merged:
    lines.append(str(network))

with open('Desktop/AWS/IPs.txt', 'w') as outfile:
    for line in lines:
        outfile.write(line)

pprint.pprint(ip_merged)

{% endhighlight %}

Whenever someone in your office complains that they can't access the resources they need you simple have them run this script. If it states that the existing range should match then you have your colleague run the script several times spaced several minutes apart. This should allow the script to catch the new IP address the ISP is using.

**Extra Credit**

You decide that having to have your colleagues run this script whenever their work is interrupted is not sufficient. You want to have the script run on a schedule and update the Security Group on it's own. You append the following to the python script to facilitate the automatic updates:

{% highlight python %}
ip_replace_contents = ''

for network in ip_merged:
  ip_replace_contents = ip_replace_contents + "\"" + str(network) "\", "
  pass
ip_replace_contents = ip_replace_contents.rstrip(", ")

replacements = {'IP_REPLACE_CONTENTS':ip_replace_contents}

with open('Desktop/Terraform/Security_Groups.tf') as infile, open('Desktop/Terraform/' + datetime.datetime.now().strftime("%Y-%m-%d") + '/Security_Groups.tf', 'w') as outfile:
    for line in infile:
        for src, target in replacements.iteritems():
            line = line.replace(src, target)
        outfile.write(line)

{% endhighlight %}

You schedule the following shell script to run every week day at 6:00 AM to update the Security Group before the work day begins:

{% highlight bash %}
#!/bin/bash

NOW=$(date +"%Y-%m-%d")

python dynamic_ips.py
terraform apply Desktop/Terraform/$NOW

{% endhighlight %}

Everyone in the office is happy knowing that the resources on AWS are safe and they don't have to worry about not being able to access them themselves.
