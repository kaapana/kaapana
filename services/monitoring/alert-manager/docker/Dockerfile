FROM docker.io/prom/alertmanager:main
# still issue CVE exists ( golang.org/x/crypto │ CVE-2023-48795 │ MEDIUM  ) need to update the docker.io/prom/alertmanager:main once new release available , 
#this should update the golang.org/x/crypto==0.16.0 to 0.17.0
LABEL IMAGE="alert-manager"
LABEL VERSION="v0.25.0"
LABEL CI_IGNORE="False"