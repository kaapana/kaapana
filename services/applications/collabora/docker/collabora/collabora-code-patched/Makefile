.PHONY: build deploy

IMAGE_NAME := "registry.hzdr.de/kaapana/public/collabora-code-patched:23.05.5.4.1"

deploy: build
	docker push $(IMAGE_NAME)

build:
	docker build -t $(IMAGE_NAME) .

coolwsd: coolwsd
	docker build --target build . -t $(IMAGE_NAME)
	$(eval ID=$(shell docker create $(IMAGE_NAME)))
	docker cp $(ID):/app/builddir/online/coolwsd - > coolwsd.tar.gz
	docker rm -v $(ID)
	tar -xvf coolwsd.tar.gz
	rm coolwsd.tar.gz
