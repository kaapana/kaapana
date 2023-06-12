#!/bin/bash

cd maintenance/app
cp -r /app/jsons/ /maintenance/app/public
npm run serve