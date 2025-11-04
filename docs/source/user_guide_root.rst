
.. raw:: html

    <style> .blue {color:blue} </style>

.. role:: blue


.. _user_guide:

User Guide
############

The following guide is meant for users of the web interface of Kaapana, providing an overview of the different views and how to use them.
This includes platform administration as well as user-specific features.
If you want to develop extensions or modify the web interface, please refer to the :ref:`Development Guide<develop_guide>`.
For information on how to install Kaapana on a :term:`server`, please refer to the :ref:`Server Installation Guide<installation_guide>`.

The navigation header
^^^^^^^^^^^^^^^^^^^^^

The top navigation bar provides quick access to essential platform and user features through a set of intuitive icons. 
Below is a description of each icon available in the header:
   
:material-regular:`info;2em;sd-text-primary` **Platform Information:** Displays details about the current Kaapana platform instance, such as chart version, build date and build-branch
Useful for identifying which version of the platform you are currently using.

:material-regular:`account_circle;2em;sd-text-primary` **Profile Information:** Opens a dropdown with user-specific information, such as username. 
From here, users can also log out.

:material-regular:`settings;2em;sd-text-primary` **User Settings:** Provides access to user preferences and customization options, such as configurations for the :ref:`datasets` view and and default settings for :ref:`workflow execution<workflow_execution>`.


:material-regular:`lightbulb;2em;sd-text-primary` **Theme toggle:** Allows users to switch between light and dark themes for the user interface. 
The selected mode is saved across sessions.

:material-outlined:`notifications;2em;sd-text-primary` **Notifications alert:** Displays system notifications, such as platform updates, warnings, or task completions. 
A badge indicator shows the number of unread notifications.


:blue:`PROJECT` **Project Selection:** Enables users to switch between :term:`projects<project>`.

.. important::
    The web interface only works properly if a :term:`project` is selected.


Navigation menu
^^^^^^^^^^^^^^^^^
The navigation menu provides quick access to all sections of the user interface.


.. toctree::
   :maxdepth: 1

   user_guide/workflows
   user_guide/store
   user_guide/meta
   user_guide/system
   user_guide/extensions



The navigation footer
^^^^^^^^^^^^^^^^^^^^^^^^^
The footer of the navigation bar contains:

:material-outlined:`help;2em;sd-text-primary` Link to the documentation.

:material-outlined:`login;2em;sd-text-primary` Logout button.

