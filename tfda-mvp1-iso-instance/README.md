# Steps to start Openstack instance and deploy platform via Ansible

## SSH key pair

Make sure you have the ssh key pair (e.g. `kaapana.pem` and `kaapana.pub`) in your `~/.ssh` folder

Also, set the ssh config file (`~/.ssh/config`) as follows:

    Host 10.128.*.*
    IdentityFile ~/.ssh/<kaapana-key-name>.pem

## Install python3-pip

Make sure you have python3 pip package installer, if not do:
    sudo apt install python3-pip

## Install requirements

Install requirements from requirements file. E.g. like with the below command:
    sudo python3 -m pip install -r requirements.txt

## Run the script with necessary arguments

Run the `start_tfda_iso_inst_with_kaapana.py` script with the necessary input parameters. You can also use the global variables inside the script to set their values
Check out the script for more details