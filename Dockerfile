FROM alpine as builder

ARG arch=amd64
ARG tidbversion=v6.6.0

WORKDIR /

RUN wget https://tiup-mirrors.pingcap.com/ctl-${tidbversion}-linux-${arch}.tar.gz && \
    tar -xzf ctl-${tidbversion}-linux-${arch}.tar.gz

FROM python:3.11-slim-buster

COPY requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

COPY --from=builder /tikv-ctl /tikv-ctl
COPY --from=builder /pd-ctl /pd-ctl

ENV PYTHONUNBUFFERED=1
COPY main.py /main.py

ENTRYPOINT [ "python3", "/main.py" ]