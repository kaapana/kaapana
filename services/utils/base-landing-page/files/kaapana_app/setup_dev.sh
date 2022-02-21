#!/bin/bash

cd landing/app
cp -r /app/jsons/ /landing/app/public
npm install
npm install local-storage-fallback
npm run build