#!/bin/sh

tensorboard --logdir=$LOG_DIR --bind_all --path_prefix=$INGRESS_PATH
