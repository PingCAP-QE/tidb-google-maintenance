#!/usr/bin/env python3

# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import subprocess
import os

import requests
from kubernetes import client, config
from google.cloud import container_v1


METADATA_URL = 'http://metadata.google.internal/computeMetadata/v1/'
METADATA_HEADERS = {'Metadata-Flavor': 'Google'}

# TODO: support non-tls cluster
# ROLE: tidb, tikv, pd
ROLE: str = os.environ["ROLE"]
TC_NAME: str = os.environ["CLUSTER_NAME"]
PD_ADDR: str = f"https://{TC_NAME}-pd:2379"

# DEBUG: bool = os.environ.get("CLUSTER_NAME") is not None
DEBUG: bool = True  # FIXME

#Init the Kubernetes client
config.load_incluster_config()
api = client.CoreV1Api()

def wait_for_maintenance():
    url = METADATA_URL + 'instance/maintenance-event'
    last_maintenance_event = None
    last_etag = '0'

    store_evicted = True  # default to true incase we miss recover store

    while True:
        time.sleep(1)
        # In case there is a network issue, retry
        try:
            r = requests.get(
                url,
                params={'last_etag': last_etag, 'wait_for_change': True},
                headers=METADATA_HEADERS)
        except requests.exceptions.ConnectionError:
            # The metadata server may not be available, so retry.
            continue    

        # During maintenance the service can return a 503, so these should
        # be retried.
        if r.status_code == 503:
            continue
        r.raise_for_status()

        last_etag = r.headers['etag']

        if r.text == 'NONE':
            maintenance_event = None
        else:
            maintenance_event = r.text

        if is_entering_maintenance(maintenance_event, last_maintenance_event):
            last_maintenance_event = maintenance_event
            if ROLE == "pd":
                resign_leader()
            elif ROLE == "tikv":
                evict_store()
                store_evicted = True
            else:
                schedule_tidb_node(True)
                delete_tidb_pod()
        elif is_during_maintenance(maintenance_event, last_maintenance_event):
            pass
        else:  # not in maintenance
            last_maintenance_event = maintenance_event
            if ROLE == "tikv":
                if store_evicted:
                    recover_restore()
                    store_evicted = False
            elif ROLE == "tidb":
                schedule_tidb_node(False)


def is_entering_maintenance(maintenance_event, last_maintenance_event) -> bool:
    return (maintenance_event is not None and
            maintenance_event != last_maintenance_event)


def is_during_maintenance(maintenance_event, last_maintenance_event) -> bool:
    return (maintenance_event is not None and
            maintenance_event == last_maintenance_event)

def evict_tidb():
    namespace = get_namespace()
    pod = get_hostname()
    patch = {"spec": {"containers": [{"name": "tidb", "image": "not-exist-image"}]}}
    api.patch_namespaced_pod(name=pod, namespace=namespace, body=patch)

def delete_tidb_pod():
    namespace = get_namespace()
    pod = get_hostname()
    api.delete_namespaced_pod(name=pod, namespace=namespace)

def get_namespace() -> str:
    with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace', 'r') as f:
        return f.read().strip()

def resign_leader():
    leader = get_leader()
    hostname = get_hostname()
    # check the current leader if it's the current instance
    # if yes, resign the leader
    # if no, do nothing
    if leader == hostname:
        cmd = f"/pd-ctl member leader resign --pd {PD_ADDR} --key /var/lib/pd-tls/tls.key --cert /var/lib/pd-tls/tls.crt --cacert /var/lib/pd-tls/ca.crt"
        print(f"resigning pd leader, cmd [{cmd}]")
        shell_cmd(cmd)

def get_leader() -> str:
    return shell_cmd(f"pd-ctl member leader show --pd {PD_ADDR} --key /var/lib/pd-tls/tls.key --cert /var/lib/pd-tls/tls.crt --cacert /var/lib/pd-tls/ca.crt | grep 'name' | cut -d: -f2").strip().strip(',').strip('"')

def get_hostname() -> str:
    return shell_cmd(f"hostname").strip()

def evict_store():
    store_id = get_store_id()
    cmd = f"/pd-ctl scheduler add evict-leader-scheduler {store_id} --pd {PD_ADDR} --key /var/lib/pd-tls/tls.key --cert /var/lib/pd-tls/tls.crt --cacert /var/lib/pd-tls/ca.crt"
    print(f"evicting store {store_id}, cmd [{cmd}]")
    shell_cmd(cmd)


def recover_restore():
    store_id = get_store_id()
    cmd = f"/pd-ctl scheduler remove evict-leader-scheduler-{store_id} --pd {PD_ADDR} --key /var/lib/pd-tls/tls.key --cert /var/lib/pd-tls/tls.crt --cacert /var/lib/pd-tls/ca.crt"
    print(f"recovering store {store_id}, cmd [{cmd}]")
    shell_cmd(cmd)


def get_store_id() -> str:
    return shell_cmd("/tikv-ctl --host 127.0.0.1:20160 --key-path /var/lib/tikv-tls/tls.key --cert-path /var/lib/tikv-tls/tls.crt --ca-path /var/lib/tikv-tls/ca.crt store | grep 'store id' | cut -d: -f2").strip()


def shell_cmd(cmd: str) -> str:
    proc = subprocess.Popen(['sh', '-c', cmd],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode:
        raise Exception(proc.returncode, stdout.decode(
            "utf8"), stderr.decode("utf8"), cmd)

    if DEBUG:
        print(f'stdout: {stdout.decode("utf8").strip()}, stderr: {stderr.decode("utf8").strip()}')

    return stdout.decode("utf8")

def schedule_tidb_node(cordon_node: bool):
    # get metadata
    # Get the project ID.
    project_id = requests.get(METADATA_URL + "project/project-id", headers=METADATA_HEADERS).text

    # Get the zone where the pod is running.
    zone = requests.get(METADATA_URL + "instance/zone", headers=METADATA_HEADERS).text
    zone = zone.split("/")[-1]

    # Get the cluster ID.
    cluster_name = requests.get(METADATA_URL + "instance/attributes/cluster-name", headers=METADATA_HEADERS).text
    cluster_id = cluster_name.split("/")[-1]

    # Get the node name.
    node_name = requests.get(METADATA_URL + "instance/hostname", headers=METADATA_HEADERS).text
    node_id = node_name.split("-")[-1]

    if DEBUG:
        print(f"project_id: {project_id}")
        print(f"zone: {zone}")
        print(f"cluster_id: {cluster_id}")
        print(f"node_id: {node_id}")

    client_v1 = container_v1.ClusterManagerClient()

    # Get the node's metadata.
    response = client_v1.get_node(project_id, zone, cluster_id, node_id)

    # Set the node's `unschedulable` flag to `True` to cordon it.
    node = response.node
    node.unschedulable = cordon_node

    # Update the node's metadata.
    update_request = container_v1.UpdateNodeRequest(
        node=node,
        name=f"projects/{project_id}/zones/{zone}/clusters/{cluster_id}/nodes/{node_id}"
    )
    client_v1.update_node(request=update_request)

    print(f"The node {node_id} in cluster {cluster_id} is now cordoned.")


def main():
    print("starting polling live-migration events...")
    wait_for_maintenance()


if __name__ == "__main__":
    main()