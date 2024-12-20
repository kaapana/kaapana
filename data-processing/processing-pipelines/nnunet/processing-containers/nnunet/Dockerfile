FROM local-only/base-nnunet-v2:latest

LABEL IMAGE="nnunet-gpu"
LABEL VERSION="03-22"
LABEL BUILD_IGNORE="False"

COPY files/ /kaapana/app/
WORKDIR /kaapana/app/

RUN apt update && apt install -y --no-install-recommends --allow-unauthenticated python3-dev

CMD ["bash","/kaapana/app/start_nnunet.sh"]