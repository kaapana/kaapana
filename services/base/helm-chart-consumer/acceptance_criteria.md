
## Configuration of Parameters
- values.yaml as source of truth for all configurable parameters in the chart.
- Then a rule based json object for parameters that are settable that contains additional rules (e.g. regex) for the parameters and also default values.
- List of values automatically set by the helm-chart-consumer
- Create a diagram on how this logic and a. + b. are used to set the chart values

## Other open points:
- How can and should we leverage helm labels ?
- Authorization:  -> Paste Lorenz's sketch here <-
- How does versioning work?
- Move the interactive workflows (workflow that starts an application) from priority MVP to Release 2.
- Should we introduce an option to scope authorization to different groups (e.g. only the PI or kaapana-system-admin can open a specific application or platform-wide dpeloyed application)


## Acceptance Criteria (Ticket)

### 1. How does the interface of a new service with following functionalities look like: chart install with values, update, uninstall, status (starting, running, failed, with a reason)
- add descriptions & rough ideas to the API endpoints


### 2. What a `helm-chart` content contains
- review helm-chart-content schema of API

### 3. How can an existing chart from a public registry be used with least amount of effort

### 4. How is the old multiinstallable concept defined with this content type, i.e. how can several copies run? How copies are listed, what an update does to running copies, what uninstall does while copies run etc
- application developers are responsible for making sure there are no conflicts
- kaapana provides the id of the helm-chart-content as variable that can be used in the helm chart as e.g. prefix for objects that could colide
- update & uninstall: each copy needs to be updated indiviudally.

### 5. Charts installed by other services with values (e.g. AII's project namespace or the image prefetch from installer) how do they interact with extension manager / Helm API?

### 6. How does the UI get the install parameters form (i.e. `extension_params` in chart annotations in the legacy code)?
- See ## Configuration of Parameters

### 7. What is required to handle the new `deployment_config` Helm charts that exist on platform charts at deploy time? And other charts that are installed through the legacy page before 0.8.0.


- [ ] A written proposal answering the above questions
- [ ] Proposal should contain API sketches that show all entry points to the service: the consumer operations used by the Extension Manager (install, update, uninstall, status of a content), and API used by the app page, AII and the installer (that is the current list, can be more)
- [ ] Reviewed with the leads and presented to developers
- [ ] Downstream issues are drafted
