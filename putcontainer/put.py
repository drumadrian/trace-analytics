from urllib import response
import boto3
from boto3.session import Session
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import ClientError
from datetime import datetime
import dns.resolver
import os 
import pprint
import json 
import time
import logging
from cmreslogging.handlers import CMRESHandler
import elasticsearch
import sys

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all


# plugins = ('ElasticBeanstalkPlugin', 'EC2Plugin', 'ECSPlugin')
# patch_all()

logging.basicConfig(level='WARNING')
logging.getLogger('aws_xray_sdk').setLevel(logging.DEBUG)


AWS_REGION_CONTAINING_ELASTICSEARCH_CLUSTER='us-west-2'
# Create our custom own session
credentials = Session().get_credentials()

handler = CMRESHandler(hosts=[{'host': 'search-s3-to-e-s3toel-16yzhw9sm8ixo-fomnghhc2ljvl7uhm2pffmnywe.us-west-2.es.amazonaws.com', 'port': 443}],
                        auth_type=CMRESHandler.AuthType.AWS_REFRESHABLE_CREDENTIALS,
                        aws_refreshable_credentials=credentials,
                        es_index_name="trace-analytics-put",
                        aws_region=AWS_REGION_CONTAINING_ELASTICSEARCH_CLUSTER,
                        use_ssl=True,
                        verify_ssl=True,
                        es_additional_fields={'App': 'trace-analytics-put', 'Environment': 'Dev'})


log = logging.getLogger("trace-analytics-put-logger")
log.setLevel(logging.INFO)
log.addHandler(handler)
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)



###########################################
#   Get the queue name to enqueue messages 
###########################################
def get_queuename():
    bytes_response = dns.resolver.query("filesqueue.loadtest.com","TXT").response.answer[0][-1].strings[0]
    response = bytes_response.decode("utf-8")
    log.error("\n filesqueue.loadtest.com= {0}\n".format(response))
    log.debug(response)
    return response


#########################################
#   Get bucketname using DNS TXT record 
#########################################
def get_bucketname():
    bytes_response = dns.resolver.query("bucket.loadtest.com","TXT").response.answer[0][-1].strings[0]
    bucketname = bytes_response.decode("utf-8")
    log.debug("\n bucket.loadtest.com= {0}\n".format(bucketname))
    return bucketname

########################################
#   Upload the local file to the bucket 
########################################
def upload_to_bucket(local_file, bucket, s3_file):
    s3 = boto3.client('s3')
    try:
        s3_response = s3.upload_file(local_file, bucket, s3_file)
        log.info("S3 Upload Successful")
        return True
    except FileNotFoundError:
        log.error("The file was not found")
        return False
    except NoCredentialsError:
        log.error("Credentials not available")
        return False



#######################################################
# Enqueue an SQS message for the Read Service to use 
#######################################################
def enqueue_object(bucketname, s3_file_name, queueURL, sqs_client):
    payload = { 
    "bucketname": bucketname, 
    "s3_file_name": s3_file_name
    }
    str_payload = json.dumps(payload)
    
    response = sqs_client.send_message(
        QueueUrl=queueURL,
        DelaySeconds=1,
        # MessageAttributes=,
        MessageBody=str_payload        
        # MessageBody=(
        #     'Information about current NY Times fiction bestseller for '
        #     'week of 12/11/2016.'
        # )
    )
    log.info("send_message() to SQS Successful\n\n")
    log.debug(response['MessageId'])



####################################
#   Upload files continuously to S3
####################################
def start_uploads(bucketname, queueURL, sqs_client):
    # interations_list = [1,2,3,4,5,6,7,8,9,10]
    # for i in interations_list:
    while True:
        #######################################
        # Start X-Ray segment 
        #######################################
        xray_recorder.begin_segment('put')
        xray_recorder.begin_subsegment('put')
        # xray_recorder.configure(service='Read Service')
        # xray_recorder.configure(plugins=plugins)
        # xray_recorder.configure(sampling=False)
        # xray_recorder.configure(context_missing='LOG_ERROR')
        xray_recorder.configure(daemon_address='0.0.0.0:2000')
        # xray_recorder.configure(sampling=False)
        # current_xray_segment = xray_recorder.current_segment()
        # segment.put_metadata("function name", "put_object_loop()")
        # subsegment = xray_recorder.begin_subsegment('annotations')

        #######################################
        # Log the current time from the system 
        #######################################
        now = datetime.now() # current date and time
        time_start = now
        time_start_string = now.strftime("%H:%M:%S.%f")
        log.debug("\n Start Interation of: start_uploads() at Time: " + time_start_string)

        s3_file_name=now.strftime("%f_%H:%M:%S.%f") + "_diagram" + ".png"
        log.info("\n s3_file_name: {0}\n".format(s3_file_name))

        uploaded = upload_to_bucket('/app/diagram.png', bucketname, s3_file_name)

        if uploaded:
            enqueue_object(bucketname, s3_file_name, queueURL, sqs_client)
        else:
            log.error("Error uploading object: {0} to bucket: {1}".format(s3_file_name, bucketname))
            now = datetime.now() # current date and time

        #######################################
        # End X-Ray segment 
        #######################################
        # segment.put_annotation('put_object_loop() duration', time_diff_string)
        # segment.put_metadata("put_object_loop() duration", time_diff_string)
        xray_recorder.end_subsegment()
        xray_recorder.end_segment()


        ###########
        # Log Data  
        ###########
        time_end = now
        time_end_string = time_end.strftime("%H:%M:%S.%f")
        log.debug("\n End Interation of: start_uploads() at Time: " + time_end_string)
        time_diff = time_end - time_start
        time_diff_string = str(time_diff)
        log.info("\n Interation Duration of: start_uploads(): " + time_diff_string)





################################################################################################################
#   Main function 
################################################################################################################
if __name__ == '__main__':

    ####################################################################################
    #  Log the list of user's environment variables and get queue url and bucket name
    ####################################################################################
    env_var = os.environ 
    log.debug("\n User's Environment variables:")

    # QUEUEURL = get_queuename()
    QUEUEURL = "https://sqs.us-west-2.amazonaws.com/696965430582/S3LoadTest-ecstaskqueuequeue6E80C2CD-14EYBYEKSI2FE"
    
    # BUCKETNAME = get_bucketname()
    BUCKETNAME = "s3loadtest-storagebucket04df299d-6wyssbwsav39"
    
    sqs_client = boto3.client('sqs')
    start_uploads(BUCKETNAME, QUEUEURL, sqs_client)
    