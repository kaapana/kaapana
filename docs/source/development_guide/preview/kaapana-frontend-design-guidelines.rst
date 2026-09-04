.. _kaapana_frontend_design_guidelines:

===================================
Kaapana Frontend Design Guidelines
===================================

Kaapana applications form one platform. The same action should look
familiar, the same status should mean the same thing, and important safeguards
should behave consistently wherever users encounter them.

These guidelines define a shared visual language and interaction rules.

.. note:: **Storybook references**

    Visual and interactive examples are identified by their path in
    :code:`@kaapana/base-ui` Storybook. Design guidance lives under :code:`Guidelines`; library
    components and APIs live under :code:`Library`.

Design principles
=================

Be consistent before being clever
---------------------------------

Use default Vuetify components and Kaapana shared components whenever possible.
Only style new components if the page genuinely needs something different, not
purely for aesthetic reasons. If it does, determine whether the new pattern
applies across applications and belongs in the shared :code:`base-ui` library. Match
its styling to the existing components.

Visual language
===============

Color
-----

Use colors by semantic role, not decoratively. The token names below are the
names used in the theme and Storybook.

.. list-table::
    :header-rows: 1
    :widths: 20 15 15 50

    * - Token
      - Light theme
      - Dark theme
      - Use
    * - :code:`primary`
      - :code:`#005BA0`
      - :code:`#42A5F5`
      - Main actions, active states, and navigation emphasis
    * - :code:`secondary`
      - :code:`#5A696E`
      - :code:`#5A696E`
      - Supporting emphasis and neutral secondary elements
    * - :code:`background`
      - :code:`#EEEEEE`
      - :code:`#121212`
      - Main application background
    * - :code:`surface`
      - :code:`#FFFFFF`
      - :code:`#1E1E1E`
      - Cards, dialogs, and primary content surfaces
    * - :code:`surface-light`
      - :code:`#F5F5F5`
      - :code:`#383838`
      - Subtle grouping, toolbars, flat alerts, and input masks
    * - :code:`surface-bright`
      - :code:`#FFFFFF`
      - :code:`#424242`
      - High-emphasis surfaces above the main surface
    * - :code:`surface-variant`
      - :code:`#424242`
      - :code:`#C8C8C8`
      - Inverted surfaces such as tooltips, badges, chips, and snackbars
    * - :code:`error`
      - :code:`#C62828`
      - :code:`#EF5350`
      - Failure, invalid state, and destructive action
    * - :code:`warning`
      - :code:`#EF6C00`
      - :code:`#FFA726`
      - Attention required without implying failure
    * - :code:`success`
      - :code:`#2E7D32`
      - :code:`#66BB6A`
      - Successful completion or positive state
    * - :code:`info`
      - :code:`#0277BD`
      - :code:`#29B6F6`
      - Neutral information and status
    * - :code:`accent`
      - :code:`#000000`
      - :code:`#FFFFFF`
      - General high-contrast accent

:code:`surface-light` is a subtle step away from the main surface. :code:`surface-variant` is
inverted—dark in the light theme and light in the dark theme—so tooltips, badges,
chips, and snackbars stand out from surrounding content.

- Use theme roles instead of local color literals.
- For filled components, use Vuetify's :code:`color` property with a semantic theme
  token. The shared theme selects a contrasting foreground automatically.
- Check contrast separately when using a theme color directly for foreground text
  or icons.
- Define every surface role explicitly; framework defaults belong to a different
  palette.
- Keep the page background visibly distinct from primary surfaces in both themes.
- Use the primary color selectively. If every action is primary, none of them is.
- Pair color with text, icons, or structure. Meaning must not depend on color
  perception alone.

**Storybook:** :code:`Guidelines / Foundations / Colors & Themes`

Typography
----------

The platform typeface is **Roboto**, using weights 300, 400, and 500. It is
bundled with the application.

Use the following Vuetify classes consistently:

.. list-table::
    :header-rows: 1
    :widths: 30 70

    * - Class
      - Use
    * - :code:`text-h4`
      - Page title
    * - :code:`text-h5`
      - Section title
    * - :code:`text-h6`
      - Content title
    * - :code:`text-subtitle-1`
      - Supporting subtitle
    * - :code:`text-body-1`
      - Body text
    * - :code:`text-body-2`
      - Secondary body text
    * - :code:`text-caption`
      - Captions and helper text
    * - :code:`text-overline`
      - Short overline labels

Use the emphasis classes independently of the type scale:

.. list-table::
    :header-rows: 1
    :widths: 30 70

    * - Class
      - Use
    * - No emphasis class
      - High-emphasis content
    * - :code:`text-medium-emphasis`
      - Supporting information
    * - :code:`text-disabled`
      - Disabled or inactive content only

- Use the platform type scale for page, section, and content titles, body text,
  captions, and supporting information.
- Use size and weight to communicate hierarchy.
- Keep labels and interface copy concise.
- Do not set a font family or a one-off font size on individual components.

**Storybook:** :code:`Guidelines / Foundations / Typography`

Spacing and shape
-----------------

.. note:: **To be decided:** Decide on the spacing scale, whether the default corner
    radius should be 4 or 8 px, and which elevation levels to use. This is just an **initial proposal**.

Use spacing in 4 px increments and an 8 px default corner radius.

Use three elevation levels:

.. list-table::
    :header-rows: 1
    :widths: 20 80

    * - Elevation
      - Use
    * - **0**
      - Flat content inside an already raised surface; pair it with a border
    * - **2**
      - Resting elevation for cards and other raised content
    * - **5**
      - Temporary overlays such as menus and dialogs

Use elevation to communicate layering, not to decorate every container. A page
should not look like a stack of floating boxes.

**Storybook:** :code:`Guidelines / Foundations / Spacing & Shape`

Layout and content width
------------------------

A view, or a component within one, should take the width its content needs
rather than the full width it is given. Left unconstrained, a layout keeps
stretching: columns drift apart, related values end up far from each other, and
lines of text outgrow a comfortable reading length, so a wide screen ends up
reading worse than a narrow one. Give the view a maximum width and let the space
beyond it become margin, with the view centered in it. On displays narrower than
that maximum, nothing changes.

Inside a view, let the leftover space fall at the trailing edge rather than
around the component: staying aligned with the content above and beside it keeps
a screen easier to scan than centering does. A container much wider than what it
holds can shrink along with it. Centering is fine for something self-contained,
such as an empty state or the content of a dialog.

Width that carries information is worth taking. Galleries, viewers, and dense
data grids can use the full width available; treat that as a choice for those
cases rather than the default.

Icons
-----

Use one recognizable symbol for each action across applications. Use the shared
semantic icon map instead of writing :code:`mdi-*` names at call sites.

Icons support labels; they do not replace them. Every icon-only control needs an
accessible name.

.. list-table::
    :header-rows: 1
    :widths: 20 30 50

    * - Name
      - MDI icon
      - Function
    * - :code:`add`
      - :code:`mdi-plus`
      - Add or create an item
    * - :code:`close`
      - :code:`mdi-close`
      - Close or dismiss the current surface
    * - :code:`confirm`
      - :code:`mdi-check`
      - Confirm or accept an action
    * - :code:`delete`
      - :code:`mdi-delete`
      - Delete or remove an item
    * - :code:`edit`
      - :code:`mdi-pencil`
      - Edit existing content
    * - :code:`error`
      - :code:`mdi-alert-circle`
      - Indicate an error or failed state
    * - :code:`expand`
      - :code:`mdi-chevron-down`
      - Expand or collapse content
    * - :code:`externalLink`
      - :code:`mdi-open-in-new`
      - Open a destination in a new context
    * - :code:`help`
      - :code:`mdi-help-circle-outline`
      - Provide contextual help
    * - :code:`info`
      - :code:`mdi-information`
      - Indicate neutral information
    * - :code:`refresh`
      - :code:`mdi-refresh`
      - Reload or refresh current data
    * - :code:`save`
      - :code:`mdi-content-save`
      - Save changes
    * - :code:`search`
      - :code:`mdi-magnify`
      - Search available content
    * - :code:`start`
      - :code:`mdi-play`
      - Start or run an operation
    * - :code:`success`
      - :code:`mdi-check-circle`
      - Indicate successful completion

**Storybook:** :code:`Guidelines / Foundations / Icons`

Actions
=======

Show what the system is doing
-----------------------------

Make loading, failure, and unavailable states visible. Users should not have to
guess whether an action was accepted, is still running, or failed.

Action hierarchy
----------------

Users should be able to distinguish the main action, supporting actions,
destructive actions, unavailable actions, warnings, and errors. Do not make
everything equally prominent.

.. list-table::
    :header-rows: 1
    :widths: 25 75

    * - Level
      - Use
    * - **Primary**
      - The main action for the current task
    * - **Secondary**
      - Supporting actions and safe dismissals such as Cancel
    * - **Tertiary**
      - Low-emphasis details, table actions, and contextual utilities
    * - **Destructive**
      - Actions that delete data, cancel work, or are difficult to undo

A dialog or task area should normally have one clearly identifiable primary
action. Button appearance may vary with context, but the hierarchy must remain
clear.

**Storybook:** :code:`Guidelines / Actions / Buttons`

Unavailable actions
-------------------

Disable an action when it exists but is temporarily unavailable. Explain why when
the reason is not obvious.

Hide an action when it does not apply in the current context or revealing it would
itself be inappropriate.

**Storybook:** :code:`Guidelines / Actions / Buttons`

Actions requiring confirmation
------------------------------

Ask for confirmation when an action is destructive or has an unusually broad
effect. Do not confirm harmless or easily reversible actions. Confirmation
fatigue makes important warnings less effective.

A confirmation must say:

1. what will happen;
2. what is affected;
3. what additional consequences follow.

Give initial focus to the safe action. Clicking outside the dialog or pressing
Escape must cancel safely.

Destructive actions
~~~~~~~~~~~~~~~~~~~

Never discard meaningful work silently. Never make an irreversible action easier
to trigger than a reversible one.

Ask for confirmation before permanently removing data, cancelling running work,
or causing consequences that are difficult to reverse.

    | **Delete workflow “Lung Segmentation”?**
    | This also deletes all jobs belonging to the workflow.
    | **Cancel** · **Delete workflow**

Make the destructive action visually distinct by giving it the :code:`error` color
variant, but never make it the initial focus.

**Storybook:** :code:`Guidelines / Patterns / Actions Requiring Confirmation / Destructive`

High-impact actions
~~~~~~~~~~~~~~~~~~~

Some actions are reversible but may consume substantial time, bandwidth, storage,
or compute resources. Ask for confirmation when users could overlook the scale or
cost.

State the scope and expected effect. Use the :code:`primary` color for confirmation;
reserve :code:`error` for destructive actions.

    | **Download dataset (86 GB)?**
    | The download may take several hours and use significant network bandwidth and
      local storage.
    | **Cancel** · **Download**

**Storybook:** :code:`Guidelines / Patterns / Actions Requiring Confirmation / High Impact`

Dialogs
-------

Choose a standard width based on the content:

.. list-table::
    :header-rows: 1
    :widths: 20 20 60

    * - Size
      - Maximum width
      - Use
    * - **Small**
      - 400 px
      - A focused confirmation or single decision
    * - **Medium**
      - 600 px
      - Forms and editing tasks
    * - **Large**
      - 900 px
      - Tables, previews, and comparisons

Content that does not fit the large size belongs in a full view, not a wider
dialog.

**Storybook:** :code:`Guidelines / Dialogs / Sizes`

Forms and editing
=================

Choosing inputs
---------------

Match the control to the data:

- use a standard selection for a short, closed list;
- use a searchable selection for a long, closed list;
- allow free-form entry only when values outside the list are valid.

Use default Vuetify components where possible, and do not add custom styling
just for aesthetic reasons. Forms should look similar across applications.

For selections displaying lists of items, consider whether presenting additional
information about each item, such as a description, status, or icon, would be
beneficial.

**Storybook:** :code:`Guidelines / Forms / Controls`

Validation
----------

Validation should help users correct input, not simply announce that it is wrong.

- Validate a field after the user interacts with it.
- Validate the complete form on submission.
- State what is required and how to fix the value.
- Keep the message close to the affected field.
- Show only relevant messages; an empty required field does not need format and
  length errors at the same time.
- Do not rely on a manually added asterisk to communicate required state.

Prefer:

    Use 3–30 characters with exactly one hyphen. Use lowercase letters or digits
    on both sides, and do not end with a hyphen. For example: :code:`lung-segmentation`.

Avoid:

    Invalid input.

**Storybook:** :code:`Guidelines / Forms / Validation`

Unsaved changes
---------------

Warn before an action would discard meaningful unsaved work. This includes
internal navigation, project or context switches, closing an edited dialog, and
leaving one editing workflow for another.

Determine whether work is unsaved by comparing the current data with its saved
or initial state. A pre-filled form is not dirty until the user changes it. Clear
the dirty state after the user saves or deliberately discards the changes.

For actions controlled by the application, show a confirmation dialog before
discarding changes. This includes closing an edited dialog, pressing Escape,
clicking outside an edited dialog, and navigating within the application. Let
users either stay and continue editing or leave and discard their changes. Give
initial focus to the safe action.

Views embedded in :code:`portal-ui` must also report their combined dirty state through
:code:`postViewDirty(dirty)` from :code:`@kaapana/base-ui`. Include unsaved work in open
dialogs when changing the project or replacing the view would discard that work.
See :doc:`Reporting Unsaved Changes (kaapana:view-dirty) <landing_page_integration>`.

The portal uses this state to protect shell-controlled navigation, such as
switching projects, opening another application, or using the shell's refresh
control. The portal does not control actions inside an embedded view, so
reporting the dirty state does not replace the application's own confirmation
dialogs.

Do not show both an application confirmation and a portal confirmation for the
same action. The component that controls the action is responsible for its
confirmation.

**Storybook:** :code:`Guidelines / Patterns / Unsaved Changes`

Feedback and system state
=========================

Loading
-------

Show progress whenever users can perceive a delay.

- Use skeleton placeholders for complex content whose expected layout is known
  and would otherwise shift noticeably while loading.
- For simple content, use a progress indicator or keep the existing layout with
  a visible loading state.
- Keep tables visible and show their table-level loading state.
- Show mutation progress on the action that started it.
- Prevent the same mutation from being submitted twice while it runs.
- If loading and displaying the complete collection does not cause performance
  problems, show all items by default.
- Otherwise, use an appropriate approach such as pagination, incremental loading,
  or infinite scrolling.

Never leave an operation, especially a destructive one, without visible feedback
after it is triggered.

**Storybook:** :code:`Guidelines / Feedback / Loading`

Errors
------

Make every failed operation visible. Explain what failed and, when possible, what
the user can do next.

Prefer:

    Could not delete the workflow. It is still running—abort it first.

Avoid:

    Request failed with status code 409.

Do not use technical detail instead of understandable user feedback. Keep it
available on demand: put the backend message, status code, or request identifier
behind a disclosure the user can open and copy.

A transient notification dismisses itself. When a failure carries such detail,
either let clicking the notification open a dialog that stays until the user
closes it, or show the failure in an inline alert or a persistent notification
instead.

**Storybook:** :code:`Guidelines / Feedback / Errors`

Notifications and alerts
------------------------

Choose the feedback mechanism based on where the information belongs and how long
it must remain available.

.. list-table::
    :header-rows: 1
    :widths: 30 70

    * - Mechanism
      - Use
    * - **Transient notification**
      - Immediate feedback about an action the user initiated
    * - **Persistent notification**
      - Important information that must remain available across applications or sessions
    * - **Inline alert**
      - Information connected to a component, form, or section of the current page

**Transient notifications** appear temporarily in the bottom-right corner. Use
them for action outcomes such as saving changes, submitting a form, starting a
workflow, beginning a download, copying a link, or failing to complete an
action.

**Inline alerts** appear close to the affected content and remain visible while
the condition is relevant. Use them for form-level information, unavailable
content, loading failures, unsupported selections, or conditions preventing the
user from continuing.

Both mechanisms can communicate success, information, warnings, or errors.
Choose based on where the feedback belongs, not its severity. Do not show the
same message both inline and as a transient notification unless it could
otherwise be missed.

**Scope:** Keep information that belongs to the current page or component local
and inline. Use a persistent notification when the user should still be able to
find the information after leaving the page, switching applications, reloading,
or returning in a later session.

Create persistent notifications through the Kaapana notifications API. The
notification service stores them, and the portal displays them in its
notification center. The portal should also show a transient notification when a
new persistent notification arrives. Do not show another local notification for
the same event.

Persistent notifications are suitable for events such as the completion of a
long-running workflow or import, a shared resource becoming unavailable, or
something requiring attention after the user leaves the originating page.

.. note:: **Goal:** In the future, enable the frontend feedback system to handle API
    errors that conform to `RFC 9457 Problem Details <https://www.rfc-editor.org/info/rfc9457/>`_.

**Storybook:** :code:`Guidelines / Feedback / Notifications & Alerts`

Empty states
------------

An empty screen should explain why it is empty:

.. list-table::
    :header-rows: 1
    :widths: 30 70

    * - State
      - Response
    * - **Nothing exists yet**
      - Explain that the collection is empty and offer the natural first action
    * - **Nothing matches**
      - Explain that filters returned no results and offer a way to clear or change them
    * - **Could not load**
      - Show an error and a recovery action; do not present failure as an empty collection

Avoid generic “No data available” text when the application knows more.

**Storybook:** :code:`Guidelines / Feedback / Empty States`

Accessibility
=============

.. note:: **Goal:** Kaapana aims to follow `WCAG 2.2 Level AA <https://www.w3.org/TR/WCAG22/>`_ accessibility standards in the future.
    The easiest initial improvements are suggested below. When choosing between
    otherwise suitable design options, prefer the more accessible option.
    See also the `WCAG 2.2 quick reference <https://www.w3.org/WAI/WCAG22/quickref/>`_ for implementation guidance.

- Make all interactive controls available by keyboard and provide a visible focus indicator.
- Maintain sufficient color contrast in light and dark themes and do not communicate meaning through color alone.
- When opening a dialog, move focus into it. When closing it, return focus to the control that opened it.
- Allow content to remain usable when users zoom or enlarge text.
- Keep validation messages and errors close to the affected control and explain
  how to correct the problem.
- Provide alternatives to dragging interactions.
- Give links and buttons clear, descriptive labels. Provide an accessible name,
  such as an :code:`aria-label`, for icon-only controls.

Review checklist
================

Before considering a screen finished, check:

- Is there an existing Vuetify or Kaapana component that meets the need?
- Is the main action obvious?
- Are destructive actions protected appropriately?
- Are unsaved changes protected during navigation?
- Can users tell when work is still running?
- Are failures visible and understandable?
- Is the full technical detail of a failure reachable on demand, without being
  shown by default?
- Does content stay within a readable width instead of stretching across the
  whole display?
- Are unavailable actions explained?
- Does every empty state explain what happened and what to do next?
- Are colors used by semantic role?
- Are icons used consistently?