import boto3
EP = "http://floci:4566"
s3 = boto3.client("s3", endpoint_url=EP, region_name="us-east-1",
                  aws_access_key_id="test", aws_secret_access_key="test")
B = "nimbus-dev-artifacts"
for o in s3.list_objects_v2(Bucket=B).get("Contents", []):
    k = o["Key"]
    print("\n========== %s (%dB) ==========" % (k, o["Size"]))
    try:
        body = s3.get_object(Bucket=B, Key=k)["Body"].read().decode("utf-8", "replace")
        print(body)
    except Exception as e:
        print("read err", e)
