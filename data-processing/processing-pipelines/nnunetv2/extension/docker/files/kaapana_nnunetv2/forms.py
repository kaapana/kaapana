"""Workflow forms. Every nnU-Net argument has a field; an empty field means nnU-Net's own default.

Frequently used fields are at the top, all others in the collapsed "Advanced (nnU-Net)" section with
nnU-Net's flag name in the title. Dropdowns of project data use the backend's installed_models mechanism
(kinds nnunetv2-raw / -preprocessed / -model, kept in sync with S3 by every step).
"""

DOCS = "/user_guide/extensions/nnunet.html"

PUBLICATION = {
    "type": "object",
    "properties": {
        "title": {
            "title": "Title",
            "default": "nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation",
            "type": "string",
            "readOnly": True,
        },
        "authors": {
            "title": "Authors",
            "default": "Isensee F., Jaeger P. F., Kohl S. A. A., Petersen J., Maier-Hein K. H.",
            "type": "string",
            "readOnly": True,
        },
        "link": {
            "title": "DOI",
            "default": "https://doi.org/10.1038/s41592-020-01008-z",
            "type": "string",
            "readOnly": True,
        },
        "confirmation": {"title": "Accept", "default": False, "type": "boolean", "required": True},
    },
}


def boolean(title, description, default=False):
    return {"title": title, "description": description, "type": "boolean", "default": default}


def text(title, description, default=None):
    field = {"title": title, "description": description, "type": "string"}
    if default is not None:
        field["default"] = default
    return field


def integer(title, description):
    return {"title": title, "description": description, "type": "integer"}


def number(title, description):
    return {"title": title, "description": description, "type": "number"}


def advanced(properties):
    # one collapsed panel holding all fields (vjsf 3 layout: a titled child group, no extra data level)
    return {
        "type": "object",
        "layout": {
            "comp": "expansion-panels",
            "children": [{"title": "Advanced (nnU-Net)", "children": list(properties)}],
        },
        "properties": properties,
    }


def selection_form(kind, title, description, empty_title, empty_description, properties):
    """A form whose first field picks one item of ``kind``; ``properties`` follow below it."""
    return {
        "type": "object",
        "title": title,
        "description": description,
        "oneOf": [],
        "models": True,
        "kind": kind,
        "empty_message": [empty_title, empty_description],
        "properties-template": properties,
    }


# ---------------------------------------------------------------- create dataset

CREATE_DATASET = {
    "type": "object",
    "properties": {
        "dataset_name": {
            "title": "Dataset name",
            "description": "Becomes DatasetXXX_<name>; the ID XXX is the next free one in this project.",
            "type": "string",
            "pattern": "^[A-Za-z0-9_-]+$",
            "required": True,
        },
        "channels": {
            "title": "Input channels",
            "description": (
                "Leave empty for one channel: the image the segmentations were drawn on. "
                "Otherwise one row per channel, in order. Rule: 'segmented' or conditions on DICOM fields "
                "joined with &, e.g. 'SeriesDescription ~ t2' (regex), 'Modality = MR', 'Tags = adc'. "
                "Each rule must match exactly one series per study."
            ),
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"title": "Name", "type": "string"},
                    "rule": {"title": "Rule", "type": "string", "default": "segmented"},
                    "normalization": {
                        "title": "Normalization",
                        "description": "Empty: CT normalization for CT, z-score otherwise.",
                        "type": "string",
                        "enum": ["", "CT", "zscore", "noNorm", "rescale_to_0_1", "rgb_to_0_1"],
                        "default": "",
                    },
                },
            },
            "default": [],
        },
        "labels": {
            "title": "Labels",
            "description": (
                "Leave empty to make every segment name its own label. Otherwise one row per label; the order "
                "gives the label value (1, 2, ...). Aliases: further segment names (comma separated) that "
                "belong to this label. Where segments overlap, the later label wins."
            ),
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"title": "Label", "type": "string"},
                    "aliases": {"title": "Also matches", "type": "string"},
                },
            },
            "default": [],
        },
        "check_only": boolean(
            "Check only", "Convert and report problems, but upload nothing. Recommended for the first run."
        ),
        "description": text("Description", "Stored in dataset.json."),
        "advanced": advanced(
            {
                "dataset_id": integer("Dataset ID", "Fixed nnU-Net dataset ID (1-999) instead of the next free one."),
                "resample_to_first_channel": boolean(
                    "Resample channels to the first channel",
                    "Channels with another geometry are resampled (linear) onto channel 0. "
                    "Off: such cases are reported as errors.",
                    True,
                ),
                "ignore_unlisted_segments": boolean(
                    "Ignore segments not in the label table", "Otherwise unknown segment names are an error."
                ),
                "skip_invalid_cases": boolean(
                    "Skip invalid cases", "Leave out cases with problems instead of failing (they are listed)."
                ),
            }
        ),
    },
}

# ---------------------------------------------------------------- plan and preprocess

PLANNERS = ["ExperimentPlanner", "nnUNetPlannerResEncM", "nnUNetPlannerResEncL", "nnUNetPlannerResEncXL"]

PLAN_PREPROCESS = selection_form(
    "nnunetv2-raw",
    "Raw dataset",
    "Raw nnU-Net dataset of this project (nnunet/raw/ in MinIO).",
    "No nnU-Net dataset in this project yet",
    "Create one with the workflow nnunetv2-create-dataset, or upload a raw dataset to nnunet/raw/ "
    "and run nnunetv2-refresh.",
    {
        "description": {"title": "Cases", "type": "string", "readOnly": True},
        "run_fingerprint": boolean(
            "Extract fingerprint", "nnUNetv2_extract_fingerprint. Off: reuse the fingerprint of an earlier run.", True
        ),
        "run_planning": boolean(
            "Plan experiment", "nnUNetv2_plan_experiment. Off: preprocess existing plans again.", True
        ),
        "run_preprocessing": boolean("Preprocess", "nnUNetv2_preprocess. Needed before training.", True),
        "planner": {
            "title": "Planner (-pl)",
            "description": (
                "ExperimentPlanner is nnU-Net's default. nnU-Net recommends the residual encoder presets: "
                "ResEncM (~9-11 GB GPU), ResEncL (~24 GB), ResEncXL (~40 GB)."
            ),
            "type": "string",
            "enum": PLANNERS,
            "default": "ExperimentPlanner",
        },
        "configurations": {
            "title": "Configurations (-c)",
            "description": "Configurations to preprocess. 3d_cascade_fullres uses the 3d_fullres data.",
            "type": "array",
            "items": {"type": "string", "enum": ["2d", "3d_fullres", "3d_lowres"]},
            "default": ["2d", "3d_fullres", "3d_lowres"],
        },
        "verify_dataset_integrity": boolean(
            "Verify dataset integrity (--verify_dataset_integrity)",
            "Recommended by nnU-Net. Runs with the fingerprint extraction.",
            True,
        ),
        "pretrained": {
            "title": "Finetune from nnFoundation",
            "description": (
                "Additionally adapt the plans to a pretrained nnFoundation checkpoint (shipped with Kaapana, "
                "CC-BY-SA-4.0) and preprocess for it (nnUNetv2_preprocess_like_nnssl). Needs 3d_fullres plans. "
                "Train the resulting ptPlans__... data with nnunetv2-train. Made for CT/MR volumes: the patch size "
                "of the pretraining (192³) is kept, so small images only get slow. A fold needs 18 GB of GPU memory."
            ),
            "type": "string",
            "oneOf": [
                {"const": "", "title": "No"},
                {"const": "nnFoundationCNN", "title": "nnFoundationCNN (ResEnc-L, 102M parameters)"},
                {"const": "nnFoundationViT", "title": "nnFoundationViT (Primus, 674M parameters)"},
            ],
            "default": "",
        },
        "advanced": advanced(
            {
                "pretrained_uploaded": text(
                    "Own pretrained checkpoint",
                    "Name of an nnssl checkpoint uploaded to nnunet/pretrained/<name>/ (adaptation_plan.json, "
                    "checkpoint_final.pth) and registered with nnunetv2-refresh. Overrides the choice above.",
                ),
                "adaptation_mode": {
                    "title": "-am (adaptation mode)",
                    "description": (
                        "How the plans are adapted to the checkpoint. Empty: nnU-Net's default (default_nnunet). "
                        "'dynamic' uses nnUNetv2_plan_like_dynamic instead (trainer DynamicPretrainedTrainer)."
                    ),
                    "type": "string",
                    "enum": ["", "default_nnunet", "like_pretrained", "no_resample", "fixed", "dynamic"],
                    "default": "",
                },
                "pretraining_name": text("-n (pretraining name)", "Names the plans. Default: the checkpoint's name."),
                "override_spacing": text("-os", "Target spacing for the 'fixed' adaptation mode, e.g. '1 1 1'."),
                "np_pretrained": integer("-np (pretrained preprocessing)", "Processes. Default: 4."),
                "clean": boolean("--clean", "Extract the fingerprint again even if one exists."),
                "planner_class": text("-pl (custom class)", "Any planner class name; overrides the planner above."),
                "plans_name": text(
                    "Plans name (-plans_name)",
                    "Plans to preprocess when 'Plan experiment' is off. Default: nnUNetPlans.",
                ),
                "fingerprint_extractor": text(
                    "-fpe", "Fingerprint extractor class. Default: DatasetFingerprintExtractor."
                ),
                "np_fingerprint": integer("-np (fingerprint)", "Processes for fingerprint extraction. Default: 8."),
                "np_preprocessing": text(
                    "-np (preprocessing)",
                    "One number, or one per configuration (e.g. '8 4 8'). Default: 2d 8, 3d_fullres 4, 3d_lowres 8.",
                ),
                "gpu_memory_target": number("-gpu_memory_target", "DANGER ZONE: custom GPU memory target in GB."),
                "preprocessor_name": text("-preprocessor_name", "DANGER ZONE: custom preprocessor class."),
                "overwrite_target_spacing": text(
                    "-overwrite_target_spacing", "DANGER ZONE: target spacing for 3d_fullres, e.g. '1.0 0.8 0.8'."
                ),
                "overwrite_plans_name": text(
                    "-overwrite_plans_name", "Plans identifier; needed with the DANGER ZONE options."
                ),
                "verbose": boolean("--verbose", "Print a lot more."),
            }
        ),
    },
)

# ---------------------------------------------------------------- train

TRAIN = selection_form(
    "nnunetv2-preprocessed",
    "Preprocessed data",
    "Dataset | plans | configuration, preprocessed in this project.",
    "No preprocessed nnU-Net data in this project yet",
    "Run the workflow nnunetv2-plan-preprocess first.",
    {
        "info": {"title": "Preprocessed", "type": "string", "readOnly": True},
        "folds": {
            "title": "Folds",
            "description": "Each selected fold trains in its own pod, in parallel if GPUs are free. "
            "'all' trains on all cases (no validation).",
            "type": "array",
            "items": {"type": "string", "enum": ["0", "1", "2", "3", "4", "all"]},
            "default": ["0", "1", "2", "3", "4"],
        },
        "gpu_memory_gb": {
            "title": "GPU memory per fold (GB)",
            "description": "Reserved on a GPU for each fold; a fold waits until a GPU has this much free. "
            "Default from the plans: 11 (nnU-Net default, ResEnc M), 18 (ResEnc L, nnFoundationCNN), "
            "32 (ResEnc XL, nnFoundationViT).",
            "type": "integer",
            "minimum": 1,
        },
        "trainer": text(
            "Trainer (-tr)",
            "nnUNetTrainer or any variant, e.g. nnUNetTrainer_250epochs, nnUNetTrainer_onlyMirror01. "
            "For nnFoundation (ptPlans) data nnUNetTrainer means PretrainedTrainer.",
            "nnUNetTrainer",
        ),
        "continue_training": boolean(
            "Continue training (--c)",
            "After a crash, timeout or abort: select the same data, folds and trainer and enable this. "
            "Resumes from the last checkpoint (nnU-Net saves one every 50 epochs).",
        ),
        "validation_only": boolean("Validation only (--val)", "Only run the validation of a finished fold."),
        "overwrite_existing": boolean("Overwrite existing fold", "Train again although the fold is finished."),
        "npz": boolean(
            "Save validation probabilities (--npz)",
            "Needed to ensemble configurations in nnunetv2-find-best-config.",
        ),
        "advanced": advanced(
            {
                "from_scratch": boolean(
                    "--from_scratch",
                    "nnFoundation plans only: train the same architecture without the pretrained weights (baseline).",
                ),
                "val_best": boolean("--val_best", "Validate with checkpoint_best instead of checkpoint_final."),
                "disable_checkpointing": boolean("--disable_checkpointing", "Write no checkpoints (testing only)."),
                "pretrained_weights": text(
                    "-pretrained_weights",
                    "Checkpoint in nnunet/ of this project, e.g. "
                    "results/Dataset001_X/nnUNetTrainer__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.safetensors",
                ),
                "n_proc_da": integer("nnUNet_n_proc_DA", "Data augmentation workers. Default: 12."),
                "splits": text(
                    "Own cross-validation splits",
                    "Empty: nnU-Net's random 5-fold split (seed 12345). To decide yourself which cases are "
                    "validated in which fold, upload a JSON file to nnunet/splits/<Dataset>/<name>.json in "
                    "the project's MinIO bucket and enter <name>. Format as nnU-Net's splits_final.json: a "
                    'list with one {"train": [...], "val": [...]} per fold, holding case names such as '
                    "Name_0000. Start from nnunet/preprocessed/<Dataset>/splits_final.json. Train all folds of "
                    "a model with the same splits. See the documentation for details.",
                ),
            }
        ),
    },
)

# ---------------------------------------------------------------- find best configuration

FIND_BEST_CONFIG = selection_form(
    "nnunetv2-model",
    "Model",
    "Any trained model of the dataset; its trainer and plans are the defaults below.",
    "No trained nnU-Net model in this project yet",
    "Train one with the workflow nnunetv2-train.",
    {
        "info": {"title": "Trained", "type": "string", "readOnly": True},
        "configurations": {
            "title": "Configurations (-c)",
            "description": "Configurations to compare. Empty: only the selected model's. "
            "Models without all folds are left out (listed in the log).",
            "type": "array",
            "items": {"type": "string", "enum": ["2d", "3d_fullres", "3d_lowres", "3d_cascade_fullres"]},
            "default": [],
        },
        "folds": {
            "title": "Folds (-f)",
            "type": "array",
            "items": {"type": "string", "enum": ["0", "1", "2", "3", "4"]},
            "default": ["0", "1", "2", "3", "4"],
        },
        "disable_ensembling": boolean(
            "No ensembles (--disable_ensembling)",
            "Ensembling needs the folds trained with --npz; disable it otherwise.",
        ),
        "advanced": advanced(
            {
                "trainers": text("-tr", "Trainers to compare (space separated). Default: the selected model's."),
                "plans": text("-p", "Plans identifiers to compare (space separated). Default: the selected model's."),
                "np": integer("-np", "Processes for ensembling and postprocessing."),
            }
        ),
    },
)

# ---------------------------------------------------------------- predict

PREDICT = selection_form(
    "nnunetv2-model",
    "Model",
    "Trained nnU-Net model of this project. Results are stored as DICOM SEG in the PACS.",
    "No trained nnU-Net model in this project yet",
    "Train one with the workflow nnunetv2-train.",
    {
        "info": {"title": "Trained", "type": "string", "readOnly": True},
        "folds": {
            "title": "Folds (-f)",
            "description": "Empty: all trained folds (ensemble).",
            "type": "array",
            "items": {"type": "string", "enum": ["0", "1", "2", "3", "4", "all"]},
            "default": [],
        },
        "apply_postprocessing": boolean(
            "Apply postprocessing",
            "The postprocessing found by nnunetv2-find-best-config for these folds, if it was run.",
            True,
        ),
        "disable_tta": boolean(
            "No test-time augmentation (--disable_tta)", "No mirroring at test time: faster, slightly less accurate."
        ),
        "seg_description": text("Series description", "Of the resulting DICOM SEG. Default: nnU-Net <dataset>."),
        "advanced": advanced(
            {
                "checkpoint": text("-chk", "Checkpoint file. Default: checkpoint_final.safetensors."),
                "step_size": number("-step_size", "Sliding window step size. Default: 0.5."),
                "npp": integer("-npp", "Preprocessing processes. Default: 3."),
                "nps": integer("-nps", "Export processes. Default: 3."),
                "not_on_device": boolean("--not_on_device", "For very large images that do not fit on the GPU."),
                "skip_invalid_cases": boolean("Skip invalid cases", "Do not fail when some series cannot be used."),
                "aetitle": {
                    **text("Result dataset", "Kaapana dataset the SEGs are added to. Default: nnunet-seg."),
                    "maxLength": 13,  # sent as DICOM AE title kp-<name>, at most 16 characters
                },
                "verbose": boolean("--verbose", "Print a lot more."),
            }
        ),
    },
)

# ---------------------------------------------------------------- refresh

REFRESH = {
    "type": "object",
    "properties": {
        "register_uploads": boolean(
            "Register uploads",
            "Folders uploaded by hand become usable after a check: nnunet/raw/DatasetXXX_Name/ (dataset.json, "
            "imagesTr, labelsTr) and nnunet/pretrained/<name>/ (adaptation_plan.json, checkpoint_final.pth).",
            True,
        ),
    },
}


def ui_forms(dag_id, workflow_form, data_form=None):
    forms = {
        "documentation_form": {"path": f"{DOCS}#{dag_id}"},  # each workflow has a section titled with its id
        "publication_form": PUBLICATION,
        "workflow_form": workflow_form,
    }
    if data_form is not None:
        forms["data_form"] = data_form
    return forms
