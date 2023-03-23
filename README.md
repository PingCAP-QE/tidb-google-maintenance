# tidb-google-maintenance

We use similar approach as [aerospike](https://github.com/aerospike/aerospike-google-maintenance/blob/master/README.md): watch GCP maintenance events on TiDB/TiKV/PD nodes and take proper actions:

- TiDB: Put the TiDB offline by cordon the TiDB node and delete the TiDB pod
  - If the node pool for TiDB instance is auto-scale, the TiDB pod is moved to other node after delete pod
  - If the node pool is not auto-scale, the TiDB pod is put offline until the node is uncordon.
- TiKV: Ecivt leaders on TiKV store during maintenance.
- PD: Resign leader if the current PD instance is the PD leader

 An additional container is added to run the maintenance watching script.

## Deploy

### Sidecar Image

Used Sidecar Public image: lobshunter/gcp-live-migration-tikv

### Add the Sidecar Image into manifest

#### For Cluster with TLS Enabled

For TiDB, add content below to spec.tidb (replace ${CLUSTR_NAME})

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
            image: lobshunter/gcp-live-migration-tikv # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
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
            image: lobshunter/gcp-live-migration-tikv # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
            name: gcp-maintenance-script
            volumeMounts:
              - name: pd-tls
                mountPath: /var/lib/pd-tls
              - name: tikv-tls
                mountPath: /var/lib/tikv-tls
```

For PD, add content below to spec.pd (replace ${CLUSTR_NAME}),

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
                value: PD
            image: lobshunter/gcp-live-migration-tikv # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
            name: gcp-maintenance-script
            volumeMounts:
              - name: pd-tls
                mountPath: /var/lib/pd-tls
              - name: tikv-tls
                mountPath: /var/lib/tikv-tls
```

#### For Cluster with TLS Disabled

For TiDB, add content below to spec.tidb (replace ${CLUSTR_NAME})

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
                <!-- FIXME -->
              - name: NODENAME
                valueFrom:
                  fieldRef:
                    fieldPath: spec.nodeName
            image: lobshunter/gcp-live-migration-tikv # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
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
            image: lobshunter/gcp-live-migration-tikv # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
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
            image: lobshunter/gcp-live-migration-tikv # NOTE: it's better to use GCR, because pulling from dockerhub can be slow
            name: gcp-maintenance-script
```

### PD scheduler configuration

Increase the PD leader-schedule limit after the cluster is deployed, through sql:

```SQL
set config pd `leader-schedule-limit`=100;
```

## Limitation

Current version is only for cluster deployed by TiDB Operator and TLS is eanbled.
