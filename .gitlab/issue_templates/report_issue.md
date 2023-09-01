## FAQ

Before you file a ticket, please have a look at our [FAQ](https://kaapana.readthedocs.io/en/stable/faq_root.html). Your problem might be covered already.

## Tag your ticket
Add the community-tech-meeting label to your ticket, otherwise we can not respond to it.

## Issue description
Give a short description of your Issue.



### All steps to reproduce the issue

1.  
2. 
3. 


### What is the expected result?

-


### What is the actual result?

-


## Additional information
Please also add logs of the involved components, wherever possible. Think about additional information you could provide, which might be helpful to identify and solve the problem. Examples include:

- Operator logs:
- DAG logs:
- Screenshot: ![Screenshot]()
- In what component is the error triggered?
- What other components of Kaapana are involved?

## Describe the system you run Kaapana on
The deployment script is able to generate a general report of your system, as well as your kaapana instance including the kubernetes status. You can create this report with: 

`./deploy_platform.sh --report > node_report.txt`

and attach the result to your ticket. If this does not work for any reason please try to provide the following information to the
best of your knowledge:
- What version of Kaapana are you running?
- What operating system are you using?
- Does your instance have a GPU and is Kaapana utilizing it?
- Is your instance connected to a registry or are you working with an offline installation?
- Is your instance running behind a proxy server?
