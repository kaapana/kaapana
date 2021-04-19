# Installation der Snapshot-VM

1) SSH in die VM 
    
    IP der VM war bei der installation: **10.1.10.46** (kann sich ändern) 
    user: racoon
    pw:   GoRACOON21

2) Plattform-Installations-Skript ausführen: **./install_racoon.sh** (befindet sich unter /home/racoon)

-> Credentials für das Installations-skript (registry credentials):

    Username: racoon
    password: EjsH53fXznKMtVFfwXxS 

4) GPU? -> yes
5) DOMAIN: IP des Servers (der Server auf dem die VMs laufen)
6) Warten bis das Deployment abgeschlossen ist
7) Überprüfung: **watch microk8s.kubectl get pods --all-namespaces**
8)  Wenn bei STATUS bei allen Einträgen "running" oder "completed" steht, ist die Installation abgeschlossen
9)  Aufruf UI der Platform über den Browser: https://DOMAIN-SERVER:8443
10) Anmeldung mit:

-> Platfform UI:

    Username: kaapana
    password: kaapana

    -> Wechsel des Passworts

12) Installation Extensions:

    - Landing page 
    - Menü: Extensions
    - Oben "version-filter" auf "All" stellen
    - code-server-chart       -> INSTALL
    - nnunet-vdev             -> INSTALL
    - racoon-train            -> INSTALL
    - radiomics-workflow-vdev -> INSTALL
    - tensorboard-chart       -> LAUNCH

13) Warten bis alle Extensions laufen
14) Überprüfen ob alle Menü-Punkte erreichbar sind
15) Überprüfen ob bei "FLOW" alle Kreise grün sind.
16) Überprüfen ob die installierten Workflows gelistet werden (kann 1-3 min dauern!):
    
    - nnunet-predict
    - nnunet-train
    - racoon-train
    - raciomics-dcmseg

17) DONE

Andere Passwörter:

-> Admin Login Keycloak (user-management von der Plattform):

    Username: racoon-admin
    password: EjsH53fXznKMtVFfwXxS

# Neue VM

Betriebssystem image:

    Ubuntu-20.04-server

Festplatten
  
    -> 200GB system -> Anpassung der System-partition auf 198GB

    -> 500GB data disk mounted at /mnt/data (fs btrfs)

credentials (initial):
  
    user: kaapana

    pw: kaapana

IP der VM:

    hostname -I

# NVIDIA Treiber 
    
    check if NVIDIA present: sudo lshw -C display
    
    sudo apt update && sudo apt upgrade -y
    sudo apt install nvidia-driver-450-server -y
    
    Stop hibernation settings:
    sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

Installation RUN-file (alternative):

    sudo bash -c "echo options nouveau modeset=0 >> /etc/modprobe.d/blacklist-nvidia-nouveau.conf"
    sudo bash -c "echo blacklist nouveau > /etc/modprobe.d/blacklist-nvidia-nouveau.conf"
    sudo dpkg --add-architecture i386 
    
    sudo apt update && sudo apt upgrade -y && sudo apt install -y libc6:i386 gcc autoconf make libglvnd-dev
    sudo reboot
    
    wget https://us.download.nvidia.com/XFree86/Linux-x86_64/460.32.03/NVIDIA-Linux-x86_64-460.32.03.run
    sudo bash NVIDIA-Linux-x86_64-460.32.03.run

**Continue Installation**  – To install Nvidia driver using the Nvidia installer

**Yes**  – To install Nvidia’s 32-bit compatible libraries

**Yes**  – To update nvidia-xconfig utility to automatically update x configuration file so that the Nvidia driver will be used when restarting X.

    sudo reboot

Testen des Treibers mit:

    nvidia-smi
     -> Tabelle mit GPU wird angezeigt 

# Installation Plattform
Benötigte Dateien aus dem zip-file:
- install_server.sh
- install_racoon.sh
- change_port_template.yaml

Benötigt werden zudem Username und Passwort für die registry am DKFZ.

Testen der HDDs:

    df -h /home -> ~200GB available
    df -h /mnt/data -> ~500GB available

install_server.sh auf die VM kopieren:

    nano install_server.sh
    den Skript-inhalt in das Terminal pasten
    strg +x -> y -> enter
    chmod +x install_server.sh

install_racoon.sh auf die VM kopieren:

    nano install_racoon.sh
    den Skript-inhalt in das Terminal pasten
    strg +x -> y -> enter
    chmod +x install_racoon.sh

change_port_template.yaml auf die VM kopieren:

    nano change_port_template.yaml
    YAML in das Terminal pasten
    strg +x -> y -> enter

Installation software dependencies:

    sudo ./install_server.sh
    Anweisungen folgen: -> no-proxy: yes
    Wenn abgeschlossen: **sudo reboot**

Installation JIP:

    ./install_racoon.sh
    username + password: **Wurde per Email geschickt**
    GPU? -> yes
    DOMAIN: IP des Servers (der Server auf dem die VMs laufen)
    Warten bis das Deployment abgeschlossen ist
    Überprüfung: **watch microk8s.kubectl get pods --all-namespaces**
    Wenn bei STATUS bei allen Einträgen "running" oder "completed" steht, ist die Installation abgeschlossen
    Aufruf UI der Platform über den Browser: https://DOMAIN-SERVER:8443

Wenn alles läuft:
    ./install_racoon.sh
    -> Uninstall platform 
    -> warten bis alles runtergefahren ist

Ubuntu-User Passwort:

    sudo passwd racoon
    -> passwort GoRACOON21

Passwörter:

-> Initiale Anmeldung Plattform:

    Username: kaapana
    password: kaapana

    -> Wechsel des Passworts auf GoRACOON21

-> Admin Login Keycloak (user-management von der Plattform):

    Username: racoon-admin
    password: EjsH53fXznKMtVFfwXxS

Verwendete Ports:
8443   -> User-interface
8081   -> Authentifizierungsserver
11113 -> DICOM port (AE-titel = dataset innerhalb der Plattform)


