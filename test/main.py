#!/usr/bin/env python3

import subprocess
import random
import time

from kubernetes import client, config

config.load_config()
api = client.CoreV1Api()


def get_namespace() -> str:
    with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace', 'r') as f:
        return f.read().strip()


# random_victim returns a random node of a tidbcluster
def random_victim():
    namespace = get_namespace()
    pods = api.list_namespaced_pod(namespace=namespace)

    pod = None
    while pod is None:
        pod = random.choice(pods.items)
        if pod.status.phase != "Running" or \
           pod.metadata.deletion_timestamp is not None or \
                not is_tidb_pod(pod):
            pod = None

    return pod.spec.node_name, pod.metadata.name


def is_tidb_pod(pod: client.V1Pod) -> bool:
    return pod.metadata.labels.get("app.kubernetes.io/component") == "tikv" or \
        pod.metadata.labels.get("app.kubernetes.io/component") == "tidb" or \
        pod.metadata.labels.get("app.kubernetes.io/component") == "pd"


def get_zone_of_node(node_name: str) -> str:
    node = api.read_node(node_name)
    return node.metadata.labels.get("failure-domain.beta.kubernetes.io/zone")


def main():
    random.seed = time.time()
    while True:
        victim_node, pod_name = random_victim()
        zone = get_zone_of_node(victim_node)
        shell_cmd(f"gcloud compute instances simulate-maintenance-event {victim_node} --zone {zone} # {pod_name}")

        sleep = random.randint(600, 1200)
        time.sleep(sleep)


def shell_cmd(cmd: str) -> str:
    debug(f'cmd: {cmd}')

    proc = subprocess.Popen(['sh', '-c', cmd],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode:
        raise Exception(proc.returncode, stdout.decode(
            "utf8"), stderr.decode("utf8"), cmd)

    return stdout.decode("utf8")


def debug(s: str):
    print(s)


if __name__ == "__main__":
    main()
