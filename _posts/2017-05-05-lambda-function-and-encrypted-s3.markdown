---
layout: "post"
title: "Lambda Function and Encrypted S3"
date: 2017-05-05T14:09:22-04:00
icon: cloud
categories:
  - AWS
  - Python
weather_temp: 60
weather_cond: day-cloudy
---

One of the aspects of AWS Lambda<sup>[1](#footnote1)</sup> that makes it excepent is that Lambda is used to extend other services offered by AWS. In this example we will set up Lambda to use Server Side Encryption for any object uploaded to AWS S3<sup>[1](#footnote2)</sup>.

The first task we have is to write the lambda function. Below we have the Python code that will read in the metadata about the object that was uploaded and copy it to the same path in the same S3 bucket if SSE is not enabled.

{% highlight python %}

import boto3
import os
import sys
import uuid

def check_if_unencrypted(bucket, key):
    s3 = boto3.resource('s3')
    obj = s3.Object('bucket_name','key')

    return not obj.server_side_encryption


def handler(event, context):
    s3 = boto3.client('s3')

    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        if check_if_unencrypted(bucket, key):
            download_path = '/tmp/{}'.format(uuid.uuid4())

            s3.download_file(bucket, key, download_path)
            data = open('test.jpg', 'rb')

            s3.put_object(Bucket=bucket, ServerSideEncryption='AES256', Body=data)

{% endhighlight %}

Now that we have out lambda function written we need to create the lambda function inside AWS. The following commands will create the AWS role for Lambda. We first need to create two files. The first is the Trust Policy for the IAM role that will allow Lambda to assume the role.

{% highlight javascript %}

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}

{% endhighlight %}

The second file will be the permissions that go along with the role. Note that these permissions give full access to the bucket. Use with caution.

{% highlight javascript %}

{
  "Version": "2012-10-17",
  "Statement": {
    "Effect": "Allow",
    "Action": "s3:*",
    "Resource": "arn:aws:s3:::example_bucket"
  },
  {
        "Effect": "Allow",
        "Action": [
          "logs:*"
        ],
        "Resource": "arn:aws:logs:*:*:*"
      }
}

{% endhighlight %}

Now that we have those two files, refered from here on as trust.json and permissions.json, we can run the commands to create the role and the lambda function.

{% highlight shell %}

aws iam create-role --role-name LambdaRole --assume-role-policy-document file://trust.json

aws iam put-role-policy --role-name LambdaRole --policy-name S3FullAccess --policy-document file://permissions.json

{% endhighlight %}

Now that we've created the role for Lambda to use we can create the function. We'll need to ZIP up the code and then upload it for Lambda to run. We will also need to the role ARN from above when we create the function.

{% highlight shell %}

zip -9 main.zip main.py

aws lambda create-function \
--region us-east-1 \
--function-name EncryptS3 \
--zip-file fileb://main.zip \
--role arn:aws:iam:us-east-1:123456789012:role:LambdaRole \
--handler main.handler \
--runtime python3.6 \
--profile adminuser \
--timeout 10 \
--memory-size 1024

{% endhighlight %}

Next we need to configure both Lambda and S3 to handle notifying Lambda when an object is places in an S3 bucket. We will need another JSON file, policy.json, with the following content that will allow the Lambda Function to access objects in the S3 bucket.


{% highlight shell %}

{
   "Statement": [
      {
         "Effect": "Allow",
         "Principal": {
            "AWS": "arn:aws:lambda:us-east-1:123456789012:function:LambdaRole"
         },
         "Action": [
            "s3:*"
         ],
         "Resource": [
            "arn:aws:s3:::example_bucket/*",
            "arn:aws:s3:::example_bucket"
         ]
      }
   ]
}

{% endhighlight %}

{% highlight shell %}

aws lambda add-permission \
--function-name EncryptS3 \
--region us-east-1 \
--statement-id some-unique-id \
--action lambda:InvokeFunction \
--principal s3.amazonaws.com \
--source-arn arn:aws:s3:::example_bucket \
--source-account 123456789012 \
--profile adminuser

aws s3api put-bucket-policy --bucket MyBucket --policy file://policy.json

aws iam create-role \
  --role-name InvokeLambdaRole \
  --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "",
          "Effect": "Allow",
          "Principal": {
            "Service": "s3.amazonaws.com"
          },
          "Action": "sts:AssumeRole",
          "Condition": {
            "StringLike": {
              "sts:ExternalId": "arn:aws:s3:::*"
            }
          }
        }
      ]
    }'

aws iam put-role-policy \
  --role-name InvokeLambdaRole \
  --policy-name InvokeLambdaPolicy \
  --policy-document '{
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "lambda:InvokeFunction"
         ],
         "Resource": [
           "*"
         ]
       }
     ]
   }'

aws s3api put-bucket-notification \
  --bucket example_bucket \
  --notification-configuration '{
    "CloudFunctionConfiguration": {
      "CloudFunction": "arn:aws:lambda:us-east-1:123456789012:function:LambdaRole",
      "InvocationRole": "arn:aws:iam:us-east-1:123456789012:role:InvokeLambdaRole",
      "Event": "s3:ObjectCreated:*"
    }
  }'

{% endhighlight %}

That's everything that's needed. You should be able to upload an object to the S3 bucket and it will be re-uploaded with Server Side Encryption. Go ahead and give it a try and let me know what you think in the comments below. If you have an questions or issues leave a comment or reach out to me on twitter.

### Footnotes

* <a name="footnote1">1</a>:[https://aws.amazon.com/lambda](https://aws.amazon.com/lambda)
* <a name="footnote2">2</a>:[https://aws.amazon.com/s3](https://aws.amazon.com/s3)
