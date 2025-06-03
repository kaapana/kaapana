.. _datasets:

Datasets
^^^^^^^^

Datasets form the core component for managing and organizing data on the platform. The features include:

* An intuitive Gallery-style view for visualizing DICOM Series thumbnails and metadata (configurable).
* Multiselect function for performing operations on multiple series simultaneously such as adding/removing to/from a dataset, executing workflows, or creating new datasets.
* A configurable side-panel metadata dashboard for exploring metadata distributions.
* Shortcut-based tagging functionality for quick and effective data annotation and categorization.
* Full-text search for filtering items based on metadata.
* A side panel series viewer using an adjusted OHIF Viewer-v3 to display DICOM next to the series metadata.
* Download functionality for selected series, allowing users to export data in DICOM format.

In the following sections, we delve into these functionalities.


Gallery View
""""""""""""
With numerous DICOMs, managing them can be challenging. Taking cues from recent photo gallery apps, we've created a similar interaction model called the "Gallery View". It displays a thumbnail of the series and its metadata, all of which is configurable via :ref:`settings`. The Gallery View loads items on-demand to ensure scalability.

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/gallery_view.gif
   :alt: Scrolling through the gallery view

In some scenarios, you may wish to structure data by patient and study. This can be achieved through the Structured Gallery View, which can be enabled in :ref:`settings`.

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/structured_gallery_view.gif
   :alt: Scrolling through the structured gallery view

The Gallery View offers straightforward and intuitive data interaction via multi-select functionality. You can select multiple individual series by holding CTRL (CMD on MacOS) and clicking the desired series, or by using the dragging functionality.

After selecting, you have several options:

* Create a new dataset from the selected data. 
* Add the selected data to an existing dataset.
* If a dataset is selected, remove the selected items from the currently selected dataset (this will not delete the data from the platform).
* Execute a workflow with the selected data. Note that in this scenario, unlike in :ref:`workflow_execution`, there is no explicit linkage to a dataset.

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/save_dataset.gif
   :alt: Saving a dataset
   :class: half-width-gif

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/add_to_dataset.gif
   :alt: Adding items to an existing dataset
   :class: half-width-gif

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/remove_from_dataset.gif
   :alt: Removing items from a dataset
   :class: half-width-gif

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/workflow.gif
   :alt: Starting a workflow
   :class: half-width-gif

.. note::
  Without an active selection, all items are selected. The 'Items Selected' indicator shows the number of items an action will be performed on.

Dataset Management and Workflow Execution
"""""""""""""""""""""""""""""""""""""""""
Interaction actions for the Gallery View are located above it. The first row is dedicated to selecting and managing datasets. Once a dataset is selected, the Gallery View will automatically update. A dataset management dialog, accessible from the same row, provides an overview of the platform's datasets and enables deletion of unnecessary datasets.

.. note::
   Deleting a dataset does *not* erase its contained data from the platform.

The second row is dedicated to filtering and searching. We offer a Lucene-based full-text search. 

.. note::
   Useful commands: 

   * Use `*` for wildcarding, e.g., `LUNG1-*` shows all series with metadata starting with `LUNG1-`.
   * Use `-` for excluding, e.g., `-CHEST` excludes all series with metadata containing `CHEST`.
   * For more information, check the `OpenSearch Documentation <https://opensearch.org/docs/latest/query-dsl/full-text/>`__.

You can add additional filters for specific DICOM tags, with an autocomplete feature for convenience.

.. note:: 
   Individual filters are combined with `AND`, while the different values within a filter are combined with `OR`.

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/search.gif
   :alt: Filtering

The following row handles tagging, a convenient way to structure data. Tags are free-text, but an autocomplete feature allows reusing existing tags. To tag a series, activate the tag(s) and then click on the series. The switch next to the tags enables tagging with multiple tags at once.

.. note::
   * Activate tags using shortcuts. Press `1` to toggle the first tag, `2` for the second, and so on.
   * If a series already has the currently active tag, clicking the series again will remove it. This also applies in multiple tags mode.
   * Remove tags by clicking the `X` next to the tag. (Note: Removing a tag this way will not update the :ref:`meta_dashboard` dashboard if it's visualized there)

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/tagging.gif
   :alt: Tagging items in the gallery view

.. _meta_dashboard:

Metadata Dashboard
""""""""""""""""""
Next to the Gallery View is the Metadata Dashboard (configurable in :ref:`settings`). This dashboard displays the metadata of the currently selected items in the Gallery View.

.. note::
  Clicking on a bar in a bar chart will set the selected value as a filter. Click 'search' to execute the query.

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/dashboard.gif
   :alt: Interacting with the Metadata Dashboard

Detail View
"""""""""""
For a more detailed look at a series, double-click a series card or click the eye icon at the top-right of the thumbnail to open the detail view in the side panel. This view comprises an OHIF-v3 viewer and a searchable metadata table for the selected series.

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/detail_view.gif
   :alt: Detail view with OHIF viewer and metadata table

.. _settings:

Settings
""""""""
Settings can be found by clicking on the gear icon in the header of the navigation bar and then selecting *DATASET CONFIGURATION*. A dialog will open.

The Dataset view is highly configurable, allowing you to tailor the display to your needs. 
You can choose between the Gallery View and Structured Gallery View, set the number of items displayed per row, and decide whether to show only thumbnails or include series metadata as well. 

Additionally, you can adjust the number of items displayed per page and specify the sorting value and direction.
For large datasets, sorting can become slow. In such cases, it is recommended to use Slicing Search: the dataset is divided into slices, and only these slices are sorted, improving performance.

For each field in the metadata, the following options are available: 

* Dashboard: Display aggregated metadata in the Metadata Dashboard
* Patient View: Display values in the patient card (if the Structured Gallery View is enabled)
* Study View: Display values in the series card (if the Structured Gallery View is enabled)
* Series Card: Display values in the Series Card
* Truncate: Limit values in the Series Card to a single line for visual alignment across series

Saving the settings will update the configuration and reload the page.

.. image:: https://www.kaapana.ai/kaapana-downloads/kaapana-docs/stable/gif/settings.gif
   :alt: Opening the settings window and adjusting the configuration.

.. note::
  For now, the configuration of Settings is only stored in the browser's local storage. Implications:

  * Clearing the browser cache will restore the default settings
  * Different users logging in from the same computer will access the same settings
  * Logging in with the same user on different computers will load the default settings
