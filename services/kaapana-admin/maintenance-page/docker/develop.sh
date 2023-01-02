#!/bin/bash
cd "$(dirname "$0")"

# sudo apt install npm
cd files/kaapana_app
npm install
npm run serve
