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

.. raw:: html

   <span class="material-icons">information_outline</span> 
   
**Platform Information:** Displays details about the current Kaapana platform instance, such as chart version, build date and build-branch
Useful for identifying which version of the platform you are currently using.

.. raw:: html

   <span class="material-icons">account_circle_outline</span>

**Profile Information:** Opens a dropdown with user-specific information, such as username. 
From here, users can also log out.

.. raw:: html

   <span class="material-icons">cog</span>

**User Settings:** Provides access to user preferences and customization options, such as configurations for the :ref:`datasets` view and and default settings for :ref:`workflow execution<workflow_execution>`.

.. raw:: html

   <span class="material-icons">lightbulb_on </span>

**Theme toggle:** Allows users to switch between light and dark themes for the user interface. 
The selected mode is saved across sessions.

.. raw:: html

   <span class="material-icons">bell</span>

**Notifications alert:** Displays system notifications, such as platform updates, warnings, or task completions. 
A badge indicator shows the number of unread notifications.


**Project Selection:** Enables users to switch between :term:`projects<project>`.

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

.. raw:: html

   <span class="material-icons">help</span> 
   

Link to the documentation.


.. raw:: html

   <span class="material-icons">login</span> 
   
Logout button.

