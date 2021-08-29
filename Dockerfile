FROM public.ecr.aws/lambda/python:3.7
RUN /var/lang/bin/python3.7 -m pip install --upgrade pip && \
    pip install boto3
