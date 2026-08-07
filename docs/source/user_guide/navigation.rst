.. _user_guide_navigation:

Navigation Menu
##################

The web interface is controlled from a collapsible sidebar on the left (not a top bar). It holds platform info, user account, settings, notifications, project selection, and links to every other page in the web interface.

Sidebar Header
==================

* **Settings** (gear icon) -- opens the settings dialog. Its **Dark Mode** and **Dev Mode** switches sit in that dialog's header, apply immediately, and are persisted per user.
* **Notifications** (bell icon) -- opens the notifications list; the icon changes to a ringing bell when unread notifications exist.
* **User** (account icon, shown when logged in) -- opens a menu with the current username and a Log Out action.
* **Project selector** -- a dropdown of the projects the current user belongs to. Archived projects are marked with an *Archived* chip, and each option shows the project's short id and your role in it. Switching projects swaps the ``/project/<short_id>`` prefix in the address bar and reloads the embedded view with the new scope; the sidebar itself is not reloaded.

Menu Sections
================

The menu is assembled at runtime from the services installed on the platform and
filtered by your roles, so it differs between deployments and between users.
A standard installation shows:

* **Home** -- the interface's landing page.
* **Workflows** -- links covered in the :ref:`Workflows guide<wms_start>`.
* **Extensions** -- covered in the :ref:`Extensions guide<extensions>`.
* **Store**, **System** and **Experimental** -- the viewers, the administrative tools and the preview UIs, mostly restricted to administrators.

Selecting an entry keeps you on the same page: the sidebar stays put and the
view is loaded into the area beside it.

Sidebar Footer
=================

* **Collapse/expand** (dock icon) -- toggles the sidebar between full width and icon-only (``mini``).
* **About** (info icon) -- opens a dialog with website, Slack and issue-tracker links, plus platform version information.
* **Help** (question-mark icon) -- opens the FAQ inside the interface, at ``/help``.
* **Log out** (exit icon) -- ends the current session.
