# tidb-google-maintenance

We use similar approach as [aerospike](https://github.com/aerospike/aerospike-google-maintenance/blob/master/README.md): watch GCP maintenance events on TiDB/TiKV/PD nodes and take proper actions:

- TiDB: Put the TiDB offline by cordon the TiDB node and delete the TiDB pod
  (the node pool of TiDB instance MUST be set to auto-scale, the cordon node is expected to be reclaimed by auto-scaler)
- TiKV: Ecivt leaders on TiKV store during maintenance.
- PD: Resign leader if the current PD instance is the PD leader

 An additional container is added to run the maintenance watching script.

## Deploy

### Sidecar Image

Used Sidecar Public image: lobshunter/tidb-gcp-live-migration

### Add the Sidecar Image into manifest

#### For Cluster with TLS Enabled

For TiDB, add content below to spec.tidb (replace ${CLUSTR_NAME})

run

```sh
# replace ${SERVICEACCOUNT}, ${NAMESPACE} and ${CLUSTR_NAME}
kubectl apply -f rbac.yaml
```

```yaml
        additionalContainers:
          - command:
              - python3
              - /main.py
            env:
              - name: TLS
                value: true
              - name: CLUSTER_NAME
                value: ${CLUSTR_NAME}
              - name: ROLE
                value: tidb
              - name: NODENAME
                valueFrom:
                  fieldRef:
                    fieldPath: spec.nodeName
            image: lobshunter/tidb-gcp-live-migration # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
            name: gcp-maintenance-script
```

For TiKV, add content below to spec.tikv (replace ${CLUSTR_NAME})

```yaml
        additionalVolumes:
          - name: pd-tls
            secret:
              secretName: ${CLUSTR_NAME}-pd-cluster-secret
        additionalContainers:
          - command:
              - python3
              - /main.py
            env:
              - name: TLS
                value: true
              - name: CLUSTER_NAME
                value: ${CLUSTR_NAME}
              - name: ROLE
                value: tikv
            image: lobshunter/tidb-gcp-live-migration # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
            name: gcp-maintenance-script
            volumeMounts:
              - name: pd-tls
                mountPath: /var/lib/pd-tls
              - name: tikv-tls
                mountPath: /var/lib/tikv-tls
```

For PD, add content below to spec.pd (replace ${CLUSTR_NAME}),

```yaml
        additionalContainers:
          - command:
              - python3
              - /main.py
            env:
              - name: TLS
                value: true
              - name: CLUSTER_NAME
                value: ${CLUSTR_NAME}
              - name: ROLE
                value: PD
            image: lobshunter/tidb-gcp-live-migration # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
            name: gcp-maintenance-script
            volumeMounts:
              - name: pd-tls
                mountPath: /var/lib/pd-tls
```

#### For Cluster with TLS Disabled

For TiDB, add content below to spec.tidb (replace ${CLUSTR_NAME})

run

```sh
# replace ${SERVICEACCOUNT}, ${NAMESPACE} and ${CLUSTR_NAME}
kubectl apply -f rbac.yaml
```

```yaml
        additionalContainers:
          - command:
              - python3
              - /main.py
            env:
              - name: TLS
                value: false
              - name: CLUSTER_NAME
                value: ${CLUSTR_NAME}
              - name: ROLE
                value: tidb
              - name: NODENAME
                valueFrom:
                  fieldRef:
                    fieldPath: spec.nodeName
            image: lobshunter/tidb-gcp-live-migration # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
            name: gcp-maintenance-script
```

For TiKV, add content below to spec.tikv (replace ${CLUSTR_NAME})

```yaml
        additionalContainers:
          - command:
              - python3
              - /main.py
            env:
              - name: TLS
                value: false
              - name: CLUSTER_NAME
                value: ${CLUSTR_NAME}
              - name: ROLE
                value: tikv
            image: lobshunter/tidb-gcp-live-migration # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
            name: gcp-maintenance-script
```

For PD, add content below to spec.pd (replace ${CLUSTR_NAME}),

```yaml
        additionalContainers:
          - command:
              - python3
              - /main.py
            env:
              - name: TLS
                value: false
              - name: CLUSTER_NAME
                value: ${CLUSTR_NAME}
              - name: ROLE
                value: PD
            image: lobshunter/tidb-gcp-live-migration # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
            name: gcp-maintenance-script
```

### PD scheduler configuration

Increase the PD leader-schedule limit after the cluster is deployed, through sql:

```SQL
set config pd `leader-schedule-limit`=100;
```

## To Simulate a GCP Maintenance Event

see: <https://cloud.google.com/compute/docs/instances/simulating-host-maintenance>
