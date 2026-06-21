import boto3
EP = "http://floci:4566"
def c(svc):
    return boto3.client(svc, endpoint_url=EP, region_name="us-east-1",
                        aws_access_key_id="test", aws_secret_access_key="test")

print("##### STS #####")
try:
    print(c("sts").get_caller_identity())
except Exception as e:
    print("sts err", e)

print("\n##### SECRETS MANAGER #####")
try:
    sm = c("secretsmanager")
    for s in sm.list_secrets().get("SecretList", []):
        name = s.get("Name")
        print("SECRET:", name, s.get("ARN"))
        try:
            v = sm.get_secret_value(SecretId=name)
            print("  VALUE:", v.get("SecretString"))
        except Exception as e:
            print("  get err", e)
except Exception as e:
    print("sm err", e)

print("\n##### SSM PARAMETERS #####")
try:
    ssm = c("ssm")
    params = ssm.describe_parameters().get("Parameters", [])
    for p in params:
        print("PARAM:", p.get("Name"))
    for p in params:
        try:
            v = ssm.get_parameter(Name=p["Name"], WithDecryption=True)
            print("  ", p["Name"], "=", v["Parameter"]["Value"])
        except Exception as e:
            print("  get err", e)
except Exception as e:
    print("ssm err", e)

print("\n##### S3 #####")
try:
    s3 = c("s3")
    for b in s3.list_buckets().get("Buckets", []):
        bn = b["Name"]
        print("BUCKET:", bn)
        try:
            for o in s3.list_objects_v2(Bucket=bn).get("Contents", []):
                print("   OBJ:", o["Key"], o["Size"])
        except Exception as e:
            print("   list err", e)
except Exception as e:
    print("s3 err", e)
