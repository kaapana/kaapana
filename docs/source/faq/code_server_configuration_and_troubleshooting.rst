Code Server: Configuration and Troubleshooting
**********************************************

Common Issues
--------------

**Code Server Not Starting**

If the Code Server fails to start, the issue is often related to **operator arguments** (for example, environment variables derived from them).

To resolve this:

1. **Check all operator arguments and environment variables.**
2. **Ensure that all values passed to `KaapanaBaseOperator` via `env_vars` are strings.**  

   - When using the Code Server, arguments **must not be set to `None`**. Use an empty string (``""``) instead if a value is not required.
   - When *not* using the Code Server, arguments can be omitted or set to `None`.
3. **Set the `dev_server` parameter correctly.**

   .. note::
      To enable the Code Server, define:
      ``dev_server="code-server"`` or ``dev_server='code-server'``.

**Key Points:**

- All keys and values in ``env_vars`` must be strings.
- Use ``""`` instead of ``None`` when running with the Code Server.
- Set ``dev_server="code-server"`` in the operator configuration.


Using the Code Server
----------------------

When developing with the **Code Server**, keep the following in mind:

1. **Manual Execution**

   Commands are **not executed automatically** inside the Code Server.  
   Use the integrated terminal to run scripts or commands manually.

2. **Typical Use Case**

   A common use case for the Code Server is to **edit or test files** inside the container environment.  
   Files from your working directory are mounted under the ``/app`` directory of the container.

3. **File Paths**

   If your code references local files using **relative paths**, update them to reflect that files reside under ``/app/``.  
   Example:  
   - Before: ``example.json``  
   - After: ``app/example.json``  
   Absolute paths remain unchanged.

4. **Operator Configuration**

   - Dockerfiles do **not** need modification to use the Code Server.
   - The **DAG file** must define ``dev_server="code-server"`` for any operator you want to debug.  
     Multiple operators in a DAG can each define this parameter.
   - The Code Server runs inside a container based on the same image as the operator.  
     The ``dev_server`` parameter only works with images based on **``base-python-cpu``**, where the Code Server dependencies are installed.
   - The Code Server does not automatically execute ``CMD`` or other final commands from the Dockerfile.  
     You must run commands manually after the container starts.

**Pitfalls Summary**

- Ensure all ``env_vars`` values are strings, as described in the *Common Issues* section.
- Update paths for files located under ``/app``.
- Commands must be executed manually inside the Code Server.
- The ``dev_server`` parameter only works with the ``base-python-cpu`` image.


Using the Code Server Extension
-------------------------------

For details on the Code Server extension (mount points, editing DAGs, inspecting workflows, etc.), see:
:ref:`extensions_code_server`.

This FAQ entry focuses on configuration and common pitfalls when using the ``dev_server`` parameter
and operator ``env_vars`` for debugging with the Code Server.
