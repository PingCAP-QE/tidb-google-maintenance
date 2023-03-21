# tidb-google-maintenance
We use similar approach as [aerospike](https://github.com/aerospike/aerospike-google-maintenance/blob/master/README.md): watch GCP maintenance events on TiKV/PD nodes and take proper actions:
- TiKV: ecivt tikv store during maintenance.
- PD: resign leader if the current PD instance is the PD leader

 An additional container is added to run the maintenance watching script.

## Deploy
### Sidecar Image
Used TiKV Sidecar Public image: lobshunter/gcp-live-migration-tikv 

### Add the Sidecar Image into manifest
For TiKV, add content below to spec.tikv (replace ${CLUSTR_NAME}), it's only for cluster deploy by TiDB Operator and TLS is eanbled.
```
        additionalVolumes:
          - name: pd-tls
            secret:
              secretName: ${CLUSTR_NAME}-pd-cluster-secret
        additionalContainers:
          - command:
              - python3
              - /main.py
            env:
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

For PD, add content below to spec.pd (replace ${CLUSTR_NAME}), it's only for cluster deploy by TiDB Operator and TLS is eanbled.
```
        additionalVolumes:
          - name: pd-tls
            secret:
              secretName: ${CLUSTR_NAME}-pd-cluster-secret
        additionalContainers:
          - command:
              - python3
              - /main.py
            env:
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
### PD scheduler configuration
Increase the PD leader-schedule limit after the cluster is deployed, through sql:
```
set config pd `leader-schedule-limit`=100;
```