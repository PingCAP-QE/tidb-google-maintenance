TIDB_VERSION ?= v7.1.0
ARCH ?= amd64
IMAGE ?= pingcap/tidb-gcp-live-migration
IMAGE_TAG ?= $(TIDB_VERSION)

image:
	docker build -t $(IMAGE):$(IMAGE_TAG) --build-arg "TIDB_VERSION=${TIDB_VERSION}" -f Dockerfile .

image-release:
	docker buildx build --platform linux/amd64,linux/arm64 --push -t $(IMAGE):$(IMAGE_TAG) --build-arg "TIDB_VERSION=${TIDB_VERSION}" -f Dockerfile .
