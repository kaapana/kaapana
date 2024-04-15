.. _black_formatter:

Code Formatting
**********************************
Black Code Formatter
---------------------

To ensure consistent code formatting in Kaapana, we utilize :code:`Black` as a precommit hook. By integrating Black into our workflow, we 
maintain a standardized coding style across the project, enhancing readability and maintainability. To write custom Operators, and 
extensions or contribute directly to Kaapana, it is suggested to use the :code:`Black` Code formatter to format your code. 
To get an overview on how the Black code formatter works, you can visit to their `Github repository <https://github.com/psf/black>`_


Installation
--------------
Black can be installed by using :code:`pip`. It requires Python 3.8+ to run. Run the following command to install via pip
:code:`pip install black`

Usage
------
After the installation any python file can be formatted just by running the file path name preceded by the black command.

.. code-block::

  black /path/to/python/file

To know more about black code style you can visit to their `Documentation <https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html>`_



Pre-commit hook
-----------------

.. important:: 
  Before commiting to the codebase, it is important to install `pre-commit hook <https://pre-commit.com/>`_. This hook check if your files follow `black <https://black.readthedocs.io/en/stable/>`_ formatting and 
  formats them accordingly if not. To install hook run this in the root of the repository: 

  .. code-block:: bash
    
      pip install pre-commit && pre-commit


Pre-commit script can be found in :code:`kaapana/utils/pre-commit`. This script uses the black formatter to detect files that do not follow 
the formatting standard while making git commits and prevent the unformatted changes from committing.