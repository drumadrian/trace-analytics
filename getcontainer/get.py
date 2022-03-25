import boto3
from boto3.session import Session
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import ClientError
from datetime import datetime
from datetime import timedelta
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
# logging.getLogger('aws_xray_sdk').setLevel(logging.DEBUG)


AWS_REGION_CONTAINING_ELASTICSEARCH_CLUSTER='us-west-2'
# Create our custom own session
credentials = Session().get_credentials()

handler = CMRESHandler(hosts=[{'host': 'search-s3-to-e-s3toel-16yzhw9sm8ixo-fomnghhc2ljvl7uhm2pffmnywe.us-west-2.es.amazonaws.com', 'port': 443}],
                        auth_type=CMRESHandler.AuthType.AWS_REFRESHABLE_CREDENTIALS,
                        aws_refreshable_credentials=credentials,
                        es_index_name="trace-analytics-get",
                        aws_region=AWS_REGION_CONTAINING_ELASTICSEARCH_CLUSTER,
                        use_ssl=True,
                        verify_ssl=True,
                        es_additional_fields={'App': 'trace-analytics-get', 'Environment': 'Dev'})


log = logging.getLogger("trace-analytics-get-logger")
log.setLevel(logging.INFO)
log.addHandler(handler)
# logging.basicConfig(stream=sys.stdout, level=logging.INFO)



################################################################################################################
#   Get the queue name to dequeue messages 
################################################################################################################
def get_queuename():
    bytes_response = dns.resolver.query("filesqueue.loadtest.com","TXT").response.answer[0][-1].strings[0]
    response = bytes_response.decode("utf-8")
    log.error("\n filesqueue.loadtest.com= {0}\n".format(response))
    log.debug(response)
    return response


################################################################################################################
#   Get messages from queue 
################################################################################################################
def dequeue_message(QUEUEURL, sqs_client):
    ###### Example of string data that was sent:#########
    # payload = { 
    # "bucketname": bucketname, 
    # "s3_file_name": s3_file_name
    # }
    ################################################
    receive_message_response = sqs_client.receive_message(
        QueueUrl=QUEUEURL,
        MaxNumberOfMessages=1
    )

    if 'Messages' in receive_message_response:
        number_of_messages = len(receive_message_response['Messages'])
        print("\n received {0} messages!! ....Processing message \n".format(number_of_messages))
    else:
        print("\n received 0 messages!! waiting.....5 seconds before retrying \n")
        time.sleep(5)
        return ["wait", "wait"]

    message_body=json.loads(receive_message_response['Messages'][0]['Body'])
    log.debug("message_body = {0} \n".format(message_body))
    bucketname = message_body['bucketname']
    objectkey = message_body['s3_file_name']

    ReceiptHandle = receive_message_response['Messages'][0]['ReceiptHandle']
    delete_message_response = sqs_client.delete_message(
    QueueUrl=QUEUEURL,
    ReceiptHandle=ReceiptHandle
    )
    log.debug("delete_message_response = {0}".format(delete_message_response))

    return [bucketname, objectkey]


################################################################################################################
#   Download files continuously from S3
################################################################################################################
def get_object_loop(QUEUEURL, sqs_client, s3_client):
    # interations_list = [1,2,3,4,5,6,7,8,9,10]
    # for i in interations_list:
    while True:
        #######################################
        # Start X-Ray segment 
        #######################################
        # xray_recorder.begin_segment('get')
        # xray_recorder.begin_subsegment('get')
        # # xray_recorder.configure(service='Read Service')
        # # xray_recorder.configure(plugins=plugins)
        # # xray_recorder.configure(sampling=False)
        # # xray_recorder.configure(context_missing='LOG_ERROR')
        # xray_recorder.configure(daemon_address='0.0.0.0:2000')
        # xray_recorder.configure(sampling=False)
        # current_xray_segment = xray_recorder.current_segment()
        # segment.put_metadata("function name", "get_object_loop()")
        # subsegment = xray_recorder.begin_subsegment('annotations')

        

        #######################################
        # Log the current time from the system 
        #######################################
        now = datetime.now() # current date and time
        time_start = now
        time_start_string = now.strftime("%H:%M:%S.%f")
        log.debug("\n Start Interation of: get_object_loop() at Time: " + time_start_string)

        #######################################
        # End X-Ray segment 
        #######################################
        # segment.put_annotation('get_object_loop() duration', time_diff_string)
        # segment.put_metadata("get_object_loop() duration", time_diff_string)
        # xray_recorder.end_subsegment()
        # xray_recorder.end_segment()


        #######################################################
        # Dequeue an SQS message enqueued by the Write Service 
        #######################################################
        message = dequeue_message(QUEUEURL, sqs_client)
        log.debug("\n message={0}\n".format(message))
        bucketname = message[0]
        objectkey = message[1]


        #######################################################
        # Dequeue an SQS message enqueued by the Write Service 
        #######################################################
        if bucketname == "wait":
            pass
        else:
            try:
                get_object_response = s3_client.get_object(
                    Bucket=bucketname,
                    Key=objectkey
                )
            except ClientError as e:
                print("Error calling get_object(): with object key {0} from bucket: {1}".format(objectkey, bucketname))
                log.error("Error calling get_object(): with object key {0} from bucket: {1}".format(objectkey, bucketname))

        ###########
        # Log Data  
        ###########
        now = datetime.now() # current date and time
        time_end = now
        time_end_string = time_end.strftime("%H:%M:%S.%f")
        log.debug("\n End Interation of: get_object_loop() at Time now: " + time_end_string)
        time_diff = time_end - time_start
        time_diff_string = str(time_diff)
        log.info("\n Interation Duration of: get_object_loop(): " + time_diff_string)

        #######################################
        # End X-Ray segment 
        #######################################
        # segment.put_annotation('get_object_loop() duration', time_diff_string)
        # segment.put_metadata("get_object_loop() duration", time_diff_string)
        # xray_recorder.end_subsegment()
        # xray_recorder.end_segment()


################################################################################################################
#   Main function 
################################################################################################################
if __name__ == '__main__':


    ################################################################################################################
    # Get and Print the list of user's environment variables 
    env_var = os.environ 
    print("\n User's Environment variables:") 
    pprint.pprint(dict(env_var), width = 1) 
    ################################################################################################################

    # log.debug("hello stdout world")
    log.info("hello AWS world from get.py")



    ################################################################################################################
    # QUEUEURL = get_queuename()
    QUEUEURL = 'https://sqs.us-west-2.amazonaws.com/696965430582/S3LoadTest-ecstaskqueuequeue6E80C2CD-14EYBYEKSI2FE'
    ################################################################################################################

    ################################################################################################################
    sqs_client = boto3.client('sqs', region_name='us-west-2')
    s3_client = boto3.client('s3', region_name='us-west-2')
    get_object_loop(QUEUEURL, sqs_client, s3_client)
    ################################################################################################################






