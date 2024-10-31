#!/bin/sh

tensorboard --logdir=$LOG_DIR --host=0.0.0.0 --path_prefix=$INGRESS_PATH
