# Installation

To run a build script install python dependencies:

`pip install -r build-scripts/requirements.txt`

# Script Structure

├── build
│   ├── __init__.py
│   ├── build_config.py
│   ├── build_helper.py
│   ├── build_state.py
│   ├── issue_tracker.py
│   ├── offline_installer_helper.py
│   └── trivy_helper.py
├── cli
│   ├── config_loader.py
│   ├── progress.py
│   └── selector.py
├── configs
│   ├── fake-values.yaml
│   └── microk8s_images.json
├── container
│   ├── __init__.py
│   ├── container.py
│   └── container_helper.py
├── helm
│   ├── __init__.py
│   ├── helm_chart.py
│   └── helm_chart_helper.py
└── utils
    ├── __init__.py
    ├── command_utils.py
    ├── git_utils.py
    └── logger.py

## Build 

Pure singleton class -> classes that are never initialized and have only class and static methods

#### build_config.py
- Pure singleton class
- Configuration from build_config.py and CLI is merged and validated in pydantic singleton class that is shared accross the whole build
- Includes only static information
  

#### build_helper.py
- Pure singleton class
- Select platform-chart
- generate build tree
- generate build graph
- generate deploy script
- generates report
- select containers to build 

#### build_state.py
- Pure singleton class
- holds all the information about the build in the singleton class and it is used throughout the whole script
- includes dynamic information -> set of containers objects, set of chart objects that are continuously updated as the build progresses

#### issue_tracker.py
- Pure singleton class
- reporting tool that collects non fatal errors and prints them at the end of the build, or immediately if exit_on_error.

#### offline_installer_helper.py
- Pure singleton class
- Helps with offline installation - downloads snap and helm packages + selected containers
  
#### trivy_helper.py
- Pure singleton class
- Helps with scans - misconfiguration scan, sbom and vuln scan


## cli

#### config_loader.py
- config parser and merger
 
#### progress.py
- rich dashboard and alive_bar progressbar helper

#### selector.py
- interactive mode

## configs
- additional configuration files

## container

- Mainly concerned about Container logic

#### container.py
- BaseImage - reference to the base image, can be local or online, of local than eventualyl resolved into container
- Container - Container parsed from Dockerfile with resolved base_images, able to build itself and push itself.
- Status - Container status

#### container_helper.py
- Pure singleton class
- Contains build and other container orchestration helper functions -> multithreading build, base-image dependency resolution, progress bar, resolving string references into objects, etc.
  
## helm
#### helm_chart.py
- HelmChart parsed from chartfile and adjacent .yaml files
- Resolved HelmChart contains its dependencies (HelmChart), collections (HelmChart), and directly used containers (for recursive dependencies traverse through dependencies and collections)
- Containes build, lint, kubeval functionality

#### helm_chart_helper.py
- Pure singleton class
- Orchestrates build, order, linting, pushing ... 

## utils
#### command_utils.py
- Pure Singleton class
- Helps with bash commands (Cannot be used everywhere as our Bash Commands differs a lot)
#### git_utils.py
- Pure Singleton class
- get git version, and branch information
#### logger.py 
- Universal logger utility -> get_logger() by default return build logger

# Build Architecture



1. Initialize config and necessarry helpers:
   1. Fill BuildConfig
   2. Create empty BuildState, ContainerHelper and ChartHelper

2. Collect containers
   1. Parse kaapana_dir for Dockerfiles (except build_ignore_patterns), create Container and BaseImage objects and store them in the BuildState. (Cannot resolve base images, as at the time of dockerfile processing, base image might not have been discovered yet!)
   2. Resolve base image string references into Containers from available containers in BuildState
   3. Getting specific container from BuildState, Charts or Other containers (base image) always gives the same Container object, therefore changes to it are global and propagated.
   
3. Collect charts
   1. Parse kaapana_dir for Chart.yaml files (except build_ignore_patterns), create HelmChart objects and store them in the BuildState under charts_available. (Cannot resolve chart dependencies or collections yet, as at the time of chartfile processing, chart dependency or collcetion might not have been discovered yet!)
   2. For workflows and dags that are discovered, additionaly check operator images to reference them as used container in the chart
   3. Resolve dependency and collection (string, version) references into HelmCharts from available containers in BuildState
   4. Changes to the HelmChart are propagates similar to point 3 from Collect containers seen above 
   5. Platform charts (should be only 1) have additionally collections and parse deployment_config.yaml file

4. Determine build targets
   1. platform_chart = BuildHelper.get_platform_chart()
   2. BuildHelper.generate_build_graph(platform_chart)
   3. BuildHelper.generate_build_tree(platform_chart)
   4. BuildHelper.generate_deployment_script(platform_chart)
    
5. Build ALL helm charts
   1. As helm charts are fast to build, we always build all charts.
   2. Building a chart means:
      1. Copy chart directory to the build directory where it belongs
         1. In case of collection-extension chart, it needs its container, that copies ready chart to be build in specific cwd. So for the chart.chart_containers[0].build_dir we set to the directory where charts/*.tgz of collection charts could be find.
      2. Lint & Kubeval chart if enabled
      3. Create .tgz file
         1. Only kaapana-admin-chart and dependencies of collection-extension chart are build (make_package)
      4. pushed to the registry - Only kaapana-admin-chart
   3. Charts are build in a specific order:
      1. Platform-chart
      2. Dependencies of platform-chart - recursively
      3. Collection of platform-chart - recursively
   4. Note: kaapana-platform-chart IS NOT a platform chart by definition, and never was. Removed deployment_config.yaml as it was never used and kaapana-type. If in the future there is a concept to use it as such, it can be changed.

6. Determine containers to build
   1. Select containers either: interactively or by using CLI
      1. If nothing is selected containers used by platform-chart and down the line are used 
   2. Select containers either: by specifying charts, or container names directly.
      1. In case of charts directly used containers and containers used as a dependency are used.
      2. In case of container names only those are built
   3. Base images for selected containers also need to be in the selected containers. (utomatic expand is happening)

7. Build and push containers
8. Process:
   1. Container without any local base images are transfered from waiting to the ready_queue.
   2. Thread picks task from ready_queue.
   3. When the tasks is finished it updates status of the Container is processed and check if any of the Container of the waiting queue have all their dependency ready (Failed, Built, etc.)
   4. Finishes when all tasks are finished.
   5. Every container is built and pushed using bash `docker build` and `docker push`
   
9. OfflineInstaller
   - Just adapted, downloads snap, helm and containers into .tgz and .tar.

10. Stop build time, generate report about used images, charts, etc.
11. Run Security Reporting if flag enabled. I adapted the code but didn't included multi-threading as it was too complicated:
    1.  Configuration Check
    2.  sboms
    3.  Vulnerability Check

# Improvements

- Documented code
  - Docstrings, comments, function and classes names
  - README

- Structured code
  - Properly defined and used staticmethods and classmethods (No method that is instance method is used as static or class method, as it was previously)
  - Removed dead code and boilerplate
  - Added Config and State classes that are shared, and it clear what type of data is accessed, compared to previous 

- Linted code
  - Type Hinting and fixing all the issue now allows to use IDE to see where the issues with the code are properly.

- Chart Linting and kubeval: With the help of fake_values.yaml, it is possible to lint and kubeval all charts now. That discovered some issues with the charts that were fixed

- Build Order
  - Removed build rounds from build scripts
  - Instead using queueing containers with all ready base images (Failed, Built, skipped, etc.)
  - This theoreticalyl improves speed, when threads do not have to wait until end of the building round to be built, but immediately when base container is built added to the queue and picked up by thread worker.
  
# Future Work

- Introduce build_extension.sh helper to build extensions (Or collections?) and introduce a guide how to install them/ update them/ remove them
- Look at the pre-installation and create a dependency order, as kaapana-platform-chart should be always installed first before extension like code-server-chart are installed.