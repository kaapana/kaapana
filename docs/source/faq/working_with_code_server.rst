Working with the Code Server
****************************

Code Server Not Starting
------------------------

If the code server fails to start, the issue may be related to **missing or incorrect custom settings/parameters** for the operator.

To resolve the issue:

1. **Check the custom settings or parameters** defined for the operator.
2. **Ensure all necessary settings are properly configured**. Specifically:
   - **When using the code server**, these settings **must not be set to `None`**. Instead, if a setting is not needed, assign it an empty string (`""`), as `None` can cause issues.
   - **When not using the code server**, these settings can either be omitted or set to `None`.

3. **Set the `dev_server` parameter correctly**:

   .. note::

       - When enabling the code server, ensure that the `dev_server` is set to `"code-server"`, with the correct syntax:
       - You can use either double quotes `"` or single quotes `'` for this assignment (e.g., `dev_server="code-server"` or `dev_server='code-server'`).

**Key Points:**

- **For code server use**: Ensure no settings are set to `None`—use an empty string (`""`) if a setting is not required.
- **Without the code server**: These settings can be omitted or set to `None`.
- **Double-check that `dev_server="code-server"` is correctly defined when enabling the code server.**



Using the Code Server: Key Considerations and Pitfalls
-------------------------------------------------------


When using the **Code Server** for development, there are several things you should be aware of to avoid common issues.

1. **Manual Start for Code**:

   - All code must be started **manually** with the required parameters. Unlike regular environments, the **Code Server** will not automatically run scripts or tasks unless specified.
   - Ensure that the required settings are passed during startup, such as the correct **Dev Server** and environment parameters.

2. **Purpose of the Code Server**:

   - The primary purpose of the **Code Server** is to **copy files from the working directory** into the `app` subfolder inside the container. These files can now be executed from there.

3. **File Path Adjustments**:

   - When files are copied into the **Code Server**, **relative paths** referencing those files will need to be updated to reflect the new directory structure. 
   - For example:
    
     - If you were referencing a file in the same directory as your code (like `example.json`), you will now need to access it as `app/example.json`.
     - **Absolute paths** (e.g., `/home/user/project/example.json`) will remain unchanged.

4. **Dockerfiles and Executions**:

   - Dockerfiles for building the container **do not need to be modified** for the purpose of using the **Code Server**.
   - The **DAG file** will need to be updated to set the correct `dev_server="code-server"` parameter for the operator that should be debugged.
   - **Important**: Only one `dev_server` should be declared in the entire file, as only the first occurrence of this parameter will be handled.
   - You can **edit the DAG file directly while the extension is deployed** using the **Code Server for Airflow Extension**. It can be found under **Extensions**, and a link to it is provided in the platform interface.
   - Keep in mind that **commands like `CMD`** or any final execution commands in the Dockerfile **won't be executed automatically** when running in the **Code Server**. Only the setup steps (like dependencies and environment configurations) will be used to build the container; the execution will need to be done manually after the container is built.

5. **Manual Configuration**:

   - All configuration parameters need to be **set manually**, especially when working with the **Code Server**. This is similar to the configuration process outlined earlier in the troubleshooting section, where:
    
     - Ensure that **required parameters** are configured properly, and that values like `dev_server="code-server"` are set correctly.
     - Remember that when using the **Code Server**, **settings must not be `None`**. If they are not required, they should be set to an empty string (`""`) instead.

Key Considerations:
-------------------
- **Paths**: Update paths referencing files after they are copied into the `/app` directory. **Absolute paths** remain unchanged.
- **Dockerfiles**: Ensure that setup and dependencies are correctly included, but remember that execution commands like `CMD` will not automatically trigger.
- **Manual Configuration**: Double-check that **all necessary parameters** are set and the `dev_server` parameter is only used once.
