#!/bin/bash
microk8s.ctr images ls | awk {'print $1'} | xargs microk8s.ctr images rm