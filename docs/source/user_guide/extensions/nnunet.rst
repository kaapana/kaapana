.. _extensions_nnunetv2:

nnU-Net
#######

| **Method:** "nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation"
| **Authors:** Isensee F., Jaeger P. F., Kohl S. A. A., Petersen J., Maier-Hein K. H.
| **DOI:** `10.1038/s41592-020-01008-z <https://doi.org/10.1038/s41592-020-01008-z>`_
| **Code:** `github.com/MIC-DKFZ/nnUNet <https://github.com/MIC-DKFZ/nnUNet>`_

The extension **nnunetv2-workflow** brings nnU-Net to Kaapana as six workflows that follow nnU-Net's own steps.
Every step runs in its own pod and every nnU-Net option is available in the workflow form:
frequently used options at the top, all others in the collapsed section *Advanced (nnU-Net)*, titled with nnU-Net's flag.
An empty field always means nnU-Net's own default. :ref:`nnunetv2-create-dataset <nnunetv2_create_dataset>` needs only
a name in the simple case; its *Advanced* section has panels for channels, labels and options.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Workflow
     - nnU-Net step
     - Result in MinIO (``<project-bucket>/nnunet/``)
   * - :ref:`nnunetv2-create-dataset <nnunetv2_create_dataset>`
     - builds the raw dataset (``nnUNet_raw``)
     - ``raw/DatasetXXX_Name/``
   * - :ref:`nnunetv2-plan-preprocess <nnunetv2_plan_preprocess>`
     - ``nnUNetv2_plan_and_preprocess``
     - ``preprocessed/DatasetXXX_Name/``
   * - :ref:`nnunetv2-train <nnunetv2_train>`
     - ``nnUNetv2_train``, one pod per fold
     - ``results/DatasetXXX_Name/<trainer>__<plans>__<configuration>/fold_X/``
   * - :ref:`nnunetv2-find-best-config <nnunetv2_find_best_config>`
     - ``nnUNetv2_find_best_configuration``
     - ``results/DatasetXXX_Name/`` (inference instructions, postprocessing)
   * - :ref:`nnunetv2-predict <nnunetv2_predict>`
     - ``nnUNetv2_predict``
     - DICOM SEG objects in the PACS
   * - :ref:`nnunetv2-refresh <nnunetv2_refresh>`
     - registers uploads, updates the dropdowns
     - \-

All data belongs to the current :ref:`project <projects>`: the folders lie in the project's MinIO bucket and the
dropdowns of the forms only show the datasets, preprocessed data and models of this project.
The folders have exactly the layout nnU-Net uses, so they can be downloaded from MinIO and used with nnU-Net
outside of Kaapana, and folders trained elsewhere can be uploaded (see :ref:`nnunetv2_uploads`).

.. note::

  The older extension *nnunet-workflow* (workflows ``nnunet-training``, ``nnunet-predict``, ...) is kept only
  for federated training (*nnunet-federated*). Use the workflows on this page for everything else.

Quick start
***********

#. Upload images and segmentations (DICOM SEG or RTSTRUCT) and put them into a Kaapana dataset,
   see :ref:`data_upload` and :ref:`datasets`.
#. Run **nnunetv2-create-dataset** on that dataset: pick the dataset, enter a name, start. If something does not
   fit, nothing is uploaded and the report says what to change, see :ref:`nnunetv2_create_report`.
#. Run **nnunetv2-plan-preprocess** on the raw dataset. The defaults are nnU-Net's defaults.
#. Run **nnunetv2-train** on the preprocessed data, e.g. *Dataset001_Liver | nnUNetPlans | 3d_fullres*.
   All five folds train in parallel as far as GPUs are free.
#. Optional: run **nnunetv2-find-best-config** once the folds of all configurations you want to compare are
   trained. It determines the best configuration (or ensemble) and the postprocessing.
#. Run **nnunetv2-predict** with the trained model on a Kaapana dataset of images. The segmentations appear as
   DICOM SEG in the dataset *nnunet-seg*.

Every run is listed in the :ref:`workflow_list`; the log of each task shows nnU-Net's output.
A failing step ends with a message that says what to change.

.. _nnunetv2_create_dataset:

nnunetv2-create-dataset
***********************

Converts images and segmentations stored in Kaapana (DICOM) into an nnU-Net raw dataset ``DatasetXXX_Name``:
the NIfTI images and label maps nnU-Net trains on, plus its ``dataset.json``.

The simple case
===============

One image per case, segmented with one or more structures: pick the Kaapana dataset (the field at the bottom of
the form), enter a name for the new dataset and start. Nothing else is needed.

* **One input channel:** the image the segmentation was drawn on.
* **One label per segment name**, numbered alphabetically. Spellings that differ only in case or spacing
  (``Liver``, ``liver``) become one label.
* **Normalization** follows nnU-Net: CT normalization for CT, z-score for everything else.

.. important::

  **Segments must not overlap.** nnU-Net needs exactly one label per voxel. If two segments share voxels (e.g. a
  lesion drawn inside the prostate segment), the run stops before anything is uploaded and names the segments
  and cases. Fix the segmentations, e.g. cut the lesion out of the prostate, see :ref:`nnunetv2_create_labels`.

The run checks everything before it uploads anything. If a check fails, nothing is uploaded and the
:ref:`report <nnunetv2_create_report>` names the problem and the field to change. Open *Advanced* only when one of
these applies:

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Situation
     - Panel in *Advanced*
   * - Several images per case (e.g. T2 + ADC), or the modality of the image is unknown
     - :ref:`Several images per case <nnunetv2_create_channels>`
   * - Segments are named differently across cases, labels should be numbered in a given order, or only some
       segments should be used
     - :ref:`Labels <nnunetv2_create_labels>`
   * - Leave out broken cases, fix the dataset ID, try without uploading
     - :ref:`Options <nnunetv2_create_options>`

How it works
============

.. code-block:: text

   Kaapana dataset (selected in the form)
     SEG "Prostate…", SEG …
          │  each SEG/RTSTRUCT references the image series it was drawn on
          ▼
   segmented series t2_tse_tra  =  one case
          │  channel rules pick series from the same study
          ▼
   study:  t2_tse_tra    → channel 0 (the segmented series)
           ep2d_diff_ADC → channel 1 (rule ~ adc)
           t1_tse_tra    → unused
          │  convert, resample to channel 0, draw segments into one label map
          ▼
   nnU-Net raw dataset
     imagesTr/Name_0000_0000.nii.gz   imagesTr/Name_0000_0001.nii.gz
     labelsTr/Name_0000.nii.gz

#. **Cases come from the segmentations.** The workflow collects every DICOM SEG and RTSTRUCT in the selected
   Kaapana dataset and follows its reference to the image series it was drawn on. **One case is one segmented
   image series.** Several segmentation objects referencing the same series (e.g. one SEG per structure) are
   merged into that case; two of them providing the same label are refused (see :ref:`nnunetv2_create_report`).
   The images themselves only need to be in the project, not in the selected dataset.
#. **Labels come from the segment names.** All segment names (SEG) and ROI names (RTSTRUCT) are collected and
   mapped to label values (see :ref:`nnunetv2_create_labels`).
#. **Channels come from the study.** For every case, each channel rule picks one series of the same study
   (see :ref:`nnunetv2_create_channels`). Without channel rows, the only channel is the segmented series.
#. **Conversion.** Each channel becomes a 3D NIfTI image; channels with another geometry than channel 0 are
   resampled onto it. All segments of the case are drawn onto the grid of the segmented image and combined into
   one label map, which is placed on the grid of channel 0.
#. **Check.** The cases, labels, overlapping segments and modalities are checked, and nnU-Net's own dataset check runs on the
   result.
#. **Report and publish.** The report lists what was found and every problem. Without problems the dataset is
   uploaded to ``nnunet/raw/DatasetXXX_Name/`` in the project's MinIO bucket, together with the report, and appears
   in the dropdown of :ref:`nnunetv2-plan-preprocess <nnunetv2_plan_preprocess>`. The ID ``XXX`` is the next free
   one in the project unless a fixed *Dataset ID* is set.

Example
=======

A prostate MRI study with three series and a SEG drawn on the T2w series:

.. code-block:: text

   Study "MRI prostate"
     #3   t2_tse_tra             MR     ◄── referenced by the SEG
     #7   ep2d_diff_ADC          MR
     #2   t1_tse_tra             MR
     #100 Prostate segmentation  SEG    segments: Prostate, Lesion
                                        (in some studies: Prostate, Tumour)

Form, in *Advanced*:

* *Several images per case*: row ``T2`` with rule ``segmented``, row ``ADC`` with rule ``SeriesDescription ~ adc``.
  Channel 0 is t2_tse_tra, channel 1 is ep2d_diff_ADC; t1_tse_tra is not used.
* *Labels*: row ``Prostate``, row ``Lesion`` with *Also matches* ``Tumour``.
  Label 1 is Prostate, label 2 is Lesion, also in the studies that call it Tumour. The Prostate segment must
  leave out the lesion voxels: segments must not overlap.

Result for the dataset name ``ProstateMR``:

.. code-block:: text

   nnunet/raw/Dataset001_ProstateMR/
     imagesTr/ProstateMR_0000_0000.nii.gz   case 0, channel 0 (T2)
     imagesTr/ProstateMR_0000_0001.nii.gz   case 0, channel 1 (ADC)
     labelsTr/ProstateMR_0000.nii.gz        0 background, 1 Prostate, 2 Lesion
     ...
     dataset.json                           channels, labels, number of cases
     kaapana.json                           rules, where every case came from
     report.txt                             the report of the run

.. _nnunetv2_create_channels:

Several images per case (multi-channel)
=======================================

Leave the table empty for one channel: the image the segmentations were drawn on. For several channels add one
row per channel, in order; the order is the channel order nnU-Net sees, also at prediction time.
The *Rule* says which series of the study is the channel:

* ``segmented``: the series the segmentation was drawn on (at most one channel).
* Conditions on the metadata fields of the series (DICOM keywords as shown in :ref:`datasets`), joined with ``&``:

  .. code-block:: text

    SeriesDescription ~ t2     regular expression, case-insensitive,
                               matches anywhere in the value
    Modality = MR              equals, case-insensitive
    Tags = adc                 Kaapana tags work like any other field
    ImageType != DERIVED       does not equal

The form marks a rule it cannot read in red before the run starts.
**Each rule must match exactly one series per study.** Rules see all series of the study in the project, not
only those in the selected dataset. Tips:

* Look up the values first: in :ref:`datasets`, open a study and compare the *Series Description* of its series
  across a few studies; scanners and sites name sequences differently. The report of a run lists, per channel,
  which series descriptions it picked and how often.
* Make regular expressions specific. ``~ t2`` also matches ``t2_tse_sag`` and ``t2_tse_cor``;
  ``~ t2.*tra`` or ``SeriesDescription ~ t2 & SeriesDescription ~ tra`` picks the axial one.
* Several patterns for the same channel: ``SeriesDescription ~ adc|apparent``.
* Exclude derived or reformatted series with ``ImageType != DERIVED``.
* If no rule can tell the series apart, tag the right series in :ref:`datasets` and use ``Tags = <tag>``.

*Name* is the channel name in ``dataset.json``. *Normalization* sets nnU-Net's intensity normalization per
channel. *Automatic* means CT normalization when all series of the channel are CT and z-score when they all
have another modality. If a channel mixes modalities or a series has no modality in the metadata, the run stops
and asks you to choose. For a single channel add one row with rule ``segmented`` and the normalization.

*Resample channels onto channel 0* (on by default) resamples channels with a different geometry (size, spacing,
orientation) linearly onto channel 0; off, such cases are reported as problems.

The rules are stored in ``kaapana.json`` and used again by :ref:`nnunetv2-predict <nnunetv2_predict>`, so
prediction finds the channels of new studies the same way.

.. _nnunetv2_create_labels:

Labels (names, merging, order)
==============================

**Empty table:** every segment name is its own label, numbered alphabetically. Names that differ only in case
or spacing are one label; the report lists the merged spellings (``Liver (also: liver)``). Names that say
nothing about the structure, such as ``Segment_1`` or ``1``, are refused because they can mean different
structures in different cases: rename the segments or fill the table.

**Table:** one row per label; the row order gives the label value (1, 2, ...). *Also matches* lists further
segment names (comma separated) that belong to the same label, e.g. label ``Lesion`` that also matches
``Tumour, tumor``. Names are compared case-insensitively; spaces in label names become ``_``.

**Segments must not overlap.** nnU-Net needs exactly one label per voxel. Kaapana does not decide which of two
overlapping segments wins, because that would change your annotation silently. If segments overlap in any case,
the run stops before anything is uploaded, also with *Skip invalid cases*, and names the segments, the voxel
count and the cases (``OVERLAP: 'Prostate' and 'Lesion' overlap in 14 case(s) ...``). To fix it:

* Correct the segmentations so that they do not share voxels, e.g. cut the lesion out of the prostate segment
  (in an annotation tool, or by exporting the segmentation again) and replace the SEGs in the Kaapana dataset.
* Or leave one of the structures out: list the labels in the table without it and enable *Ignore segments not
  in the label table*.

Overlaps between segments of the *same* label (e.g. ``Tumour`` and ``tumor`` merged into one label) are fine.

Segment names found in the data but not in the table stop the workflow before anything is converted (the error
lists them). Add them as label or in *Also matches*, or enable *Ignore segments not in the label table* to leave
them out; the report lists the ignored names. A label that has no voxel in any case is a problem as well.

nnU-Net's region-based training (nested labels as in BraTS) is not supported: every voxel has exactly one label.

Supported segmentations: DICOM SEG (binary, fractional – thresholded at 50 % – and labelmap) and RTSTRUCT (closed
planar contours; a contour inside another contour of the same ROI is a hole). SEG frames must lie on the slices
of the referenced image; segmentations resampled to another grid are reported as errors.

.. _nnunetv2_create_options:

Options
=======

* **Check only:** convert and report, but upload nothing and keep the dataset ID free. A normal run with problems
  uploads nothing either, so this is only needed to look at the report of a clean dataset first.
* **Skip invalid cases:** cases with problems are left out and listed instead of failing the run. Problems of the
  whole dataset (overlapping segments, mixed modalities, empty labels) still fail it.
* **Dataset ID:** a fixed nnU-Net dataset ID (1–999) instead of the next free one.
* **Description:** stored in ``dataset.json``.

.. _nnunetv2_create_report:

Reading the report
==================

Every run prints a report at the end of its log (Workflow List → the run → *Open the Airflow run details* →
task *nnunet-create-dataset* → *Logs*). A published dataset also contains it as ``report.txt``.

.. code-block:: text

   Dataset:   Dataset001_ProstateMR
   Cases:     20 of 20 segmented series, from 20 patient(s)
   Channels:
     0 T2 (segmented): MR x20; normalization zscore; series: t2_tse_tra x18, t2_blade_tra x2
     1 ADC (SeriesDescription ~ adc): MR x20; normalization zscore; series: ep2d_diff_ADC x20
   Labels:
     1 Prostate: in 20 of 20 cases
     2 Lesion: in 14 of 20 cases (also: lesion)

Check *series* (did each rule pick the intended sequence everywhere?) and the label counts.
If some patients have several cases, the report suggests own cross-validation splits
(see :ref:`nnunetv2_splits`).

Problems are listed below the report and make the run fail. Problems of single cases can be left out with
*Skip invalid cases*; then the valid cases are uploaded and the others only listed. Series are named
``#<series number> <series description>`` as in the viewer.

``channel 'ADC' (SeriesDescription ~ adc) matches no series; the study has: #3 t2_tse_tra, #5 dwi_b800``
   The study has no such series, or it is named differently. Compare with the listed series; widen the rule
   (``~ adc|apparent``) or skip the case.

``channel 'T2' (...) matches 2 series: #3 t2_tse_tra, #4 t2_tse_tra_ND``
   The rule is not specific enough; add a condition (``& SeriesDescription ~ tra``, ``& ImageType != DERIVED``).

``two channels picked the same series``
   Two rules match the same series; make them exclusive.

``OVERLAP: 'Prostate' and 'Lesion' overlap in 14 case(s), ... voxels in total: #3 t2_tse_tra (patient P07), ...``
   nnU-Net needs one label per voxel. Fix the segmentations of the listed cases so that the two segments do not
   share voxels, or leave one of them out (see :ref:`nnunetv2_create_labels`). This always stops the run.

``these segment names do not say which structure they are ...``
   Segments named like ``Segment_1``. Rename them in the data, or list the labels in the table.

``these segment names are in the data but not in the label table: ...``
   Add the names as label or in *Also matches*, or enable *Ignore segments not in the label table*.

``'x' is listed for two labels``
   A name or alias appears in two rows; keep it in one.

``label 'Lesion' comes from 2 segmentation objects (...)``
   Two segmentation objects of the same series contain the same structure, e.g. a second annotator, an outdated
   version or an earlier nnU-Net prediction (dataset *nnunet-seg*). Keep only one of them in the Kaapana dataset.

``label 'x' has no voxel in any case``
   The label is in the table but never drawn. Remove the row.

``the segmentation is empty (no voxel of any label)``
   All segments of the case are empty or ignored. Remove the case or skip it.

``channel 0 (...) has mixed or unknown modalities (CT x18, unknown x2) ...``
   The normalization cannot be chosen automatically. Add a channel row with the normalization, see
   :ref:`nnunetv2_create_channels`.

``cannot be read`` / ``does not reference an image series``
   The SEG/RTSTRUCT is broken or lacks the reference to the image it was drawn on, so it cannot be placed.
   Export it again with the reference, or remove it from the dataset.

``the SEG frames do not lie on the pixel grid of the referenced image``
   The SEG was resampled or drawn on another series than it references. Export it again on the original image.

``only N of M files ... form one volume (several stacks, localizers or missing slices?)``
   The series is not a single 3D volume. Remove localizers or split the stacks before importing.

``channel 1 has a different geometry than channel 0``
   Only with resampling switched off: enable *Resample channels onto channel 0*.

``nnU-Net's dataset check failed: ...``
   nnU-Net's own check (``verify_dataset_integrity``) found a problem in the converted files; the message is
   nnU-Net's.

``The dataset contains no DICOM SEG or RTSTRUCT``
   Add the segmentation series (not only the images) to the Kaapana dataset.

What is written
===============

* ``imagesTr/<Name>_<case>_<channel>.nii.gz`` and ``labelsTr/<Name>_<case>.nii.gz``: one entry per case,
  numbered from ``0000``; label maps are ``uint8`` on the grid of channel 0.
* ``dataset.json``: nnU-Net's description (``channel_names``, ``labels``, ``numTraining``, ``file_ending``).
* ``kaapana.json``: the channel rules, labels and aliases, and for every case its study, the series of each
  channel and the segmentation objects – to trace a case back to its DICOM data, and for prediction.
* ``report.txt``: the report of the run.

The dataset is uploaded only when complete (a ``_DONE.json`` marker is written last), so other workflows never
see half a dataset. To add cases later, create a new dataset; existing datasets are not changed.

.. _nnunetv2_plan_preprocess:

nnunetv2-plan-preprocess
************************

Runs nnU-Net's fingerprint extraction, experiment planning and preprocessing (``nnUNetv2_plan_and_preprocess``)
for a raw dataset. Each of the three steps can be switched off, e.g. to preprocess existing plans again.

* **Planner (-pl):** ``ExperimentPlanner`` is nnU-Net's default. nnU-Net recommends the residual encoder presets
  for new projects: ``nnUNetPlannerResEncM`` (GPU with ~9-11 GB), ``nnUNetPlannerResEncL`` (~24 GB),
  ``nnUNetPlannerResEncXL`` (~40 GB). See :ref:`nnunetv2_resources`.
* **Configurations (-c):** the configurations to preprocess. Configurations that nnU-Net does not plan for the
  dataset (e.g. ``3d_lowres`` for small images) are left out with a note in the log.

Every preprocessed configuration appears in the dropdown of :ref:`nnunetv2-train <nnunetv2_train>` as
*Dataset | plans | configuration*.

.. _nnunetv2_nnfoundation:

Finetuning from nnFoundation
============================

*Finetune from nnFoundation* adapts the plans to a pretrained checkpoint and preprocesses the data for it
(``nnUNetv2_preprocess_like_nnssl``). Two checkpoints of the
`nnFoundation <https://huggingface.co/MIC-DKFZ>`_ models are shipped with Kaapana (license CC-BY-SA-4.0),
nothing is downloaded:

* **nnFoundationCNN:** ResEnc-L, 102M parameters.
* **nnFoundationViT:** Primus, 674M parameters.

The adaptation needs normal plans with a ``3d_fullres`` configuration, so keep *Plan experiment* enabled in the
first run. The result is an additional entry *Dataset | ptPlans__<checkpoint>__... | 3d_fullres* in
:ref:`nnunetv2-train <nnunetv2_train>`, which then uses nnU-Net's ``PretrainedTrainer`` automatically.
Use *--from_scratch* in the training form to train the same architecture without the pretrained weights as a
baseline.

.. warning::

  The adapted plans keep the patch size of the pretraining (192×192×192 for nnFoundationCNN). nnFoundation is made
  for CT and MR volumes of at least this size; smaller images are padded, which makes every epoch slow without
  any benefit. A fold also needs 18 GB of GPU memory (nnFoundationViT: 32 GB), see :ref:`nnunetv2_resources`.

Own pretrained checkpoints (from `nnssl <https://github.com/MIC-DKFZ/nnssl>`_) can be uploaded, see
:ref:`nnunetv2_uploads`, and selected with *Own pretrained checkpoint* in *Advanced*. The adaptation mode
(``-am``) and the other options of ``nnUNetv2_preprocess_like_nnssl`` are in *Advanced* as well.

.. _nnunetv2_train:

nnunetv2-train
**************

Trains the selected preprocessed data (``nnUNetv2_train``). Every selected fold runs in its own pod; the folds of
a run train in parallel as far as GPUs are free. Folds that are not selected appear as *skipped* in the run.

* **Folds:** ``0``-``4`` are nnU-Net's 5-fold cross-validation and needed for
  :ref:`nnunetv2-find-best-config <nnunetv2_find_best_config>`. ``all`` trains on all cases without validation.
* **GPU memory per fold (GB):** reserved on a GPU for each fold; a fold starts when a GPU has this much free.
  The default comes from the plans, see :ref:`nnunetv2_resources`.
* **Trainer (-tr):** ``nnUNetTrainer`` or any variant that ships with nnU-Net, e.g. ``nnUNetTrainer_250epochs``.
  For nnFoundation plans the default becomes ``PretrainedTrainer``.
* **--npz:** saves the softmax predictions of the validation. Needed to ensemble configurations in
  :ref:`nnunetv2-find-best-config <nnunetv2_find_best_config>`.

A fold that is already trained is not trained again unless *Overwrite existing fold* is enabled.
The finished fold is published as ``results/<Dataset>/<trainer>__<plans>__<configuration>/fold_X/``.

Fields in *Advanced* include *Own cross-validation splits*, see :ref:`nnunetv2_splits`.

.. _nnunetv2_splits:

Own cross-validation splits
===========================

By default nnU-Net splits the cases of a dataset at random into 5 folds (seed 12345) and writes the split to
``nnunet/preprocessed/<Dataset>/splits_final.json``. You can give nnU-Net your own split instead, e.g. to keep
all scans of one patient in the same fold, to stratify by site or scanner, or to reuse the folds of a
publication.

#. Download ``nnunet/preprocessed/<Dataset>/splits_final.json`` from the project's MinIO bucket (see
   :ref:`store`). It already contains every case name of the dataset and is the easiest starting point.
#. Edit it. The file is a list with one entry per fold; each entry names the training and the validation cases
   of that fold:

   .. code-block:: json

     [
       {"train": ["Liver_0002", "Liver_0003", "Liver_0004"], "val": ["Liver_0000", "Liver_0001"]},
       {"train": ["Liver_0000", "Liver_0001", "Liver_0004"], "val": ["Liver_0002", "Liver_0003"]}
     ]

   Case names are the file names in ``labelsTr/`` without ``.nii.gz``. Usually every case is validated in
   exactly one fold, but nnU-Net does not enforce this.
#. Upload it as ``nnunet/splits/<Dataset>/<name>.json``, e.g. ``nnunet/splits/Dataset001_Liver/by_patient.json``.
   One dataset can have several split files.
#. In **nnunetv2-train** open *Advanced* and enter ``<name>`` (``by_patient``) in *Own cross-validation splits*.

Before nnU-Net starts, each fold checks the file: it must be valid JSON in the format above, every case must
exist in the preprocessed data and the file must define the selected fold. Otherwise the fold fails with a
message that names the problem and lists the split files available for the dataset. The name and checksum of the
split used are recorded with the fold's results. The fold ``all`` trains on all cases and ignores the split.

.. warning::

  The results of a fold are stored under ``<trainer>__<plans>__<configuration>/fold_X/`` regardless of the split.
  Train all folds of one model with the same split, and use the same split for every configuration compared in
  :ref:`nnunetv2-find-best-config <nnunetv2_find_best_config>`: otherwise the validation results are not
  comparable and an ensemble validates cases that one of its models was trained on. To retrain a model with a
  different split, enable *Overwrite existing fold* for all its folds.

  The form offers the folds ``0``-``4``. A split file with more folds can be uploaded, but only its first five
  folds can be trained.

.. _nnunetv2_continue_training:

Continue a crashed or cancelled training
========================================

While a fold trains, its checkpoints are published to MinIO whenever nnU-Net writes them, and the training log
every 10 minutes. If a training crashed, ran into the timeout or was aborted in the :ref:`workflow_list`:

#. Start **nnunetv2-train** again with the same preprocessed data, fold and trainer.
#. Enable **Continue training (--c)**.

The training resumes from the last published checkpoint. nnU-Net writes this checkpoint every 50 epochs, so up to
50 epochs are trained again. *Validation only (--val)* runs only the validation of a fold whose training is
finished, e.g. after the validation failed.

.. _nnunetv2_find_best_config:

nnunetv2-find-best-config
*************************

Runs ``nnUNetv2_find_best_configuration``: compares the cross-validation results of the trained configurations,
optionally of ensembles of two configurations, and determines the postprocessing.

Select any trained model of the dataset. Its trainer and plans are the defaults; *Configurations (-c)* selects
which configurations to compare. Only models with all selected folds trained are compared; the others are
listed in the log. Ensembling needs all folds trained with *--npz*; otherwise enable *--disable_ensembling*.

The log ends with nnU-Net's inference instructions (best configuration and how to predict with it). The
postprocessing found here is applied by :ref:`nnunetv2-predict <nnunetv2_predict>` by default.

.. _nnunetv2_predict:

nnunetv2-predict
****************

Segments the images of a Kaapana dataset with a trained model and stores the result as DICOM SEG in the PACS,
in the Kaapana dataset *nnunet-seg* (change it with *Result dataset* in *Advanced*, at most 13 characters).

**Input:** a Kaapana dataset of image series; every series is one case. For models with several channels, the
selected series is the channel ``segmented`` and the other channels are found in its study with the rules that
were used to create the training dataset.

* **Folds (-f):** empty uses all trained folds as an ensemble.
* **Apply postprocessing:** applies the postprocessing found by
  :ref:`nnunetv2-find-best-config <nnunetv2_find_best_config>` for these folds, if it was run.
* **--disable_tta:** no mirroring at test time; faster, slightly less accurate.

.. _nnunetv2_refresh:

nnunetv2-refresh
****************

Updates the dropdowns of the forms from MinIO and registers folders that were uploaded by hand
(see :ref:`nnunetv2_uploads`). Leftovers of interrupted uploads are removed.

.. _nnunetv2_uploads:

Using data from outside Kaapana
*******************************

Upload the folders with the MinIO browser (see :ref:`store`) into the project bucket and run
**nnunetv2-refresh**:

* **Raw dataset:** ``nnunet/raw/DatasetXXX_Name/`` with ``dataset.json``, ``imagesTr/`` and ``labelsTr/``, exactly
  as nnU-Net expects it. The ID must not be used by another dataset of the project.
* **Pretrained checkpoint:** ``nnunet/pretrained/<name>/`` with ``adaptation_plan.json`` and
  ``checkpoint_final.pth`` from nnssl.

The refresh checks the files and then makes them available in the forms. Folders under ``nnunet/`` are only
used once a step or the refresh has completed them: every step uploads into a temporary folder first and marks
the result as complete at the end, so a crashed run never leaves half-written data behind.

To use a model in nnU-Net outside of Kaapana, download ``nnunet/results/<Dataset>/`` from MinIO.

.. _nnunetv2_resources:

Resources
*********

The resources follow nnU-Net's
`hardware recommendations <https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/installation_instructions.md>`_:

.. list-table::
   :header-rows: 1

   * - Step
     - CPU (request / limit)
     - RAM (request / limit)
     - GPU memory
     - Timeout
   * - create-dataset
     - 4 / 8 cores
     - 8 / 32 GB
     - \-
     - 12 hours
   * - plan-preprocess
     - 8 / 12 cores
     - 16 / 64 GB
     - \-
     - 1 day
   * - train (per fold)
     - 12 / 16 cores
     - 16 / 64 GB
     - from the plans, see below
     - 7 days
   * - find-best-config
     - 4 / 8 cores
     - 8 / 64 GB
     - \-
     - 1 day
   * - predict
     - 4 / 8 cores
     - 16 / 48 GB
     - 6 GB
     - 12 hours

nnU-Net uses 12 data augmentation workers by default (*nnUNet_n_proc_DA* in the training form);
nnU-Net recommends more for fast GPUs.

Each fold reserves the GPU memory its plans need, so folds that fit share a GPU and larger ones get a GPU of
their own. The default of *GPU memory per fold* in the training form is:

.. list-table::
   :header-rows: 1

   * - Plans
     - GPU memory per fold
   * - nnU-Net default (``ExperimentPlanner``), ``nnUNetPlannerResEncM``
     - 11 GB
   * - ``nnUNetPlannerResEncL``, nnFoundationCNN
     - 18 GB
   * - ``nnUNetPlannerResEncXL``, nnFoundationViT
     - 32 GB
   * - own ``-gpu_memory_target`` in plan-preprocess
     - that value

nnU-Net designs ResEnc L for GPUs with 24 GB and ResEnc XL for 40 GB; the values above are what a training
actually uses (measured for ResEnc L, estimated for XL and the ViT). Change the value in the form if a training
runs out of GPU memory or needs less.

If no GPU can ever free the requested memory, the run fails at once with a message instead of waiting: e.g. when
programs outside Kaapana occupy part of the GPU.

The container image contains nnU-Net, PyTorch and the nnFoundation checkpoints and is about 10 GB large;
the first run on a node takes several minutes to pull it.

nnU-Net version
***************

nnU-Net is installed unchanged from a fixed commit of its ``master`` branch, because nnFoundation is not part
of a release yet. The commit is recorded in the metadata of every result (``_DONE.*.json`` files next to the
results in MinIO), together with the form values that produced it.

Troubleshooting
***************

**The workflows are not in the Workflow Execution list.**
  Workflows of a newly installed extension are enabled automatically only for projects created afterwards.
  For existing projects an admin enables them in *System > Projects > (project) > Project Workflows*.
  The list itself is refreshed once per minute.

**The form shows old fields after an update of the extension.**
  Restart the Airflow webserver (``kubectl rollout restart deployment/airflow-webserver -n services``) and reload
  the page.

**A dropdown is empty although the data is in MinIO.**
  Run **nnunetv2-refresh**.

**nnunetv2-create-dataset fails.**
  The report at the end of the log lists every problem and what to change, see :ref:`nnunetv2_create_report`.
  Overlapping segments, mixed modalities and empty labels always stop the run; problems of single cases can be
  left out with *Skip invalid cases*.

**nnunetv2-train fails with "A fold needs ... GB of GPU memory".**
  No GPU can provide the memory in *GPU memory per fold*, because the GPU is too small or other programs use part
  of it. Free the GPU or lower the value.

**Ensembling fails because .npz files are missing.**
  Train the folds again with *--npz* (enable *Validation only* to only rerun the validation), or enable
  *--disable_ensembling*.
