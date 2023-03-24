FROM google/cloud-sdk:slim

WORKDIR /

COPY requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

ENV PYTHONUNBUFFERED=1
COPY main.py /main.py

ENTRYPOINT [ "python3", "/main.py" ]