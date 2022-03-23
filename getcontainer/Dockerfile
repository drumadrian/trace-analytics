##############################
# REFERENCES
##############################
# https://stackoverflow.com/questions/19537645/get-environment-variable-value-in-dockerfile
# https://www.dynatrace.com/support/help/technology-support/cloud-platforms/other-platforms/docker/installation-and-operation/deploy-dynatrace-oneagent-as-docker-container/
# https://www.dynatrace.com/support/help/technology-support/cloud-platforms/amazon-web-services/integrations/deploy-oneagent-on-aws-fargate/#expand-2512build-time-injection


##############################
# Required Input arguments, Default values
##############################
FROM amazonlinux                                


##############################
# Build base container
##############################
RUN mkdir /app
# COPY ./diagram.png /app/diagram.png
# ADD ./load-test.sh /app/load-test.sh
# RUN ls -al /app/load-test.sh
# RUN chmod 755 /app/load-test.sh
RUN yum install -y aws-cli datetime
RUN yum install -y wget unzip
RUN yum install -y python3-pip python3 python3-setuptools
COPY requirements.txt /
RUN pip3 install --user -r requirements.txt
ADD ./get.py /app/get.py
# ENTRYPOINT ["sh", "-c","/app/load-test.sh"]
# ENTRYPOINT ["python3","/app/load-test.py"]


##############################
# start Python app
##############################
# CMD [ "executable", "param1", "param2" ] # the command of your application, for example, Java
CMD [ "python3", "/app/get.py" ] # the command of the application






