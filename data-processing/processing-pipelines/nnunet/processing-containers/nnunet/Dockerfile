FROM local-only/base-nnunet:03-22

LABEL IMAGE="nnunet-gpu"
LABEL VERSION="03-22"
LABEL CI_IGNORE="False"

ENV EXPERIMENT_NAME "unknown_experiment"

COPY files/ /kaapanasrc/
WORKDIR /kaapanasrc/
CMD ["bash","/kaapanasrc/start_nnunet.sh"]