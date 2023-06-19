ARG TIDB_VERSION=v6.6.0

FROM pingcap/pd:${TIDB_VERSION} as pd-builder
FROM pingcap/tikv:${TIDB_VERSION} as tikv-builder

FROM library/python:3.11-slim-buster

COPY requirements.txt /requirements.txt
RUN pip3 install -r /requirements.txt

COPY --from=tikv-builder /tikv-ctl /tikv-ctl
COPY --from=pd-builder /pd-ctl /pd-ctl

ENV PYTHONUNBUFFERED=1
COPY main.py /main.py

ENTRYPOINT [ "python3", "/main.py" ]