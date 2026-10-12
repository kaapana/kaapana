// server.js
//
// Kaapana-integrated backend for the split-viewer application. Rewritten
// from the original standalone version:
// - PACS access goes through dicom-web-filter-service (project-aware,
//   authenticated) instead of raw, unauthenticated dcm4chee-arc.
// - Segmentation no longer runs inline (TotalSegmentator/dcmqi/dcm2niix are
//   not even installed in this image anymore) - it triggers the already-built
//   auto-segmentation-pipeline Airflow DAG via Kaapana's own job API instead,
//   which does body-part inference and TotalSegmentator v2 execution properly.
// - Auth is never minted here: every request reaching this backend has
//   already passed through Kaapana's Traefik + oauth2-proxy gateway, which
//   injects x-forwarded-access-token / x-forwarded-preferred-username - the
//   same pattern collabora's own wopi backend uses
//   (services/applications/collabora/docker/wopi/files/app/dependencies.py).
//   Those headers are simply forwarded to the Kaapana-internal services
//   called on the caller's behalf.
import express from "express";
import axios from "axios";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
app.use(express.json({ limit: "1mb" }));
app.use((req, res, next) => {
  req.setTimeout(0);
  res.setTimeout(0);
  next();
});

// ==== ENV / CONFIG ====
// In-cluster service DNS names - same convention every Kaapana operator/
// backend in this codebase uses (e.g. dicom-web-filter-service.services.svc).
const DICOM_WEB_FILTER_URL =
  process.env.DICOM_WEB_FILTER_URL || "http://dicom-web-filter-service.services.svc:8080";
const KAAPANA_BACKEND_URL =
  process.env.KAAPANA_BACKEND_URL || "http://kaapana-backend-service.services.svc:5000";
const AUTO_SEGMENTATION_DAG_ID = "auto-segmentation-pipeline";

const log = (...a) => console.log(new Date().toISOString(), ...a);

// ==== Auth forwarding ====
function authHeaders(req, accept = "application/json") {
  const h = { Accept: accept };
  const token =
    req.headers["x-forwarded-access-token"] ||
    (req.headers["authorization"] || "").split(" ").pop();
  if (token) h.Authorization = `Bearer ${token}`;
  return h;
}

// GetInputOperator (every DAG's first task) requires conf_data.project_form
// with the full project record (opensearch_index, s3_bucket, ...) - POST
// /client/job doesn't resolve this server-side (unlike POST /client/workflow,
// which injects it via its own get_project dependency), so it's the caller's
// job. The native Kaapana frontend keeps the active project's *full* record
// in its Vuex store; this backend only has the "Project" cookie the frontend
// also sets ({name, id} only - see store/modules/project.module.ts), so it
// resolves the full record from aii-service by that id.
async function resolveProjectForm(req) {
  const cookieHeader = req.headers.cookie || "";
  const match = cookieHeader
    .split(";")
    .map((s) => s.trim())
    .find((s) => s.startsWith("Project="));
  if (!match) return null;

  let projectId;
  try {
    projectId = JSON.parse(decodeURIComponent(match.slice("Project=".length))).id;
  } catch (e) {
    log("Failed to parse Project cookie", e?.message);
    return null;
  }
  if (!projectId) return null;

  try {
    const resp = await axios.get(`http://aii-service.services.svc:8080/projects/${projectId}`, {
      headers: authHeaders(req),
    });
    return resp.data;
  } catch (e) {
    log("Failed to resolve project_form from aii-service", e?.response?.data || e?.message);
    return null;
  }
}

function forwardedUsername(req) {
  return req.headers["x-forwarded-preferred-username"];
}

// ==== DICOMweb QIDO-RS helpers, against dicom-web-filter ====
async function qidoStudies(req, params) {
  const res = await axios.get(`${DICOM_WEB_FILTER_URL}/studies`, {
    params,
    headers: authHeaders(req),
  });
  return res.data;
}

async function qidoSeries(req, studyUID, params) {
  const res = await axios.get(
    `${DICOM_WEB_FILTER_URL}/studies/${encodeURIComponent(studyUID)}/series`,
    { params, headers: authHeaders(req) }
  );
  return res.data;
}

async function qidoInstances(req, studyUID, seriesUID, params) {
  const res = await axios.get(
    `${DICOM_WEB_FILTER_URL}/studies/${encodeURIComponent(studyUID)}/series/${encodeURIComponent(
      seriesUID
    )}/instances`,
    { params, headers: authHeaders(req) }
  );
  return res.data;
}

// ==== DICOM JSON accessors ====
function getValue(item, tag, def = undefined) {
  const v = item?.[tag]?.Value?.[0];
  return v === undefined ? def : v;
}

function getCodeMeaning(item, seqTag) {
  const seq = item?.[seqTag]?.Value;
  if (!seq) return undefined;
  for (const seqItem of seq) {
    const v = seqItem?.["00080104"]?.Value?.[0];
    if (v !== undefined) return v;
  }
  return undefined;
}

// ==== Body-part canonicalization ====
// Ported from auto-segmentation-pipeline's BodyPartInferenceOperator.py (same
// tag list, same priority order, same canonical bucket set) so a radiology
// segment's label (e.g. TotalSegmentator's "kidney_left") and a pathology
// series' own DICOM tags (e.g. SeriesDescription "Kidney biopsy") both reduce
// to the same canonical term and can be matched against each other -
// matching organ identity, not an exact string.
const TAGS_TO_CHECK = [
  ["00180015", "value"], // BodyPartExamined
  ["00082218", "codeMeaning"], // Anatomic Region Sequence
  ["00081084", "codeMeaning"], // Admitting Diagnoses Code Sequence
  ["00081030", "value"], // StudyDescription
  ["0008103E", "value"], // SeriesDescription
  ["00081080", "value"], // Admitting Diagnoses Description
  ["00321060", "value"], // Requested Procedure Description
  ["00321030", "value"], // Reason for Study
  ["00181030", "value"], // Protocol Name
];

const BODY_PART_TO_CANONICAL = {
  heart: "heart",
  liver: "liver",
  spleen: "spleen",
  kidney: "kidney",
  kidneys: "kidney",
  lung: "lung",
  lungs: "lung",
  aorta: "aorta",
  brain: "brain",
  prostate: "prostate",
};

function canonicalizeBodyPart(value) {
  if (!value) return undefined;
  const simple = String(value)
    .toLowerCase()
    .replace(/[^a-z ]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (simple in BODY_PART_TO_CANONICAL) return BODY_PART_TO_CANONICAL[simple];
  for (const key of Object.keys(BODY_PART_TO_CANONICAL)) {
    if (simple.includes(key)) return BODY_PART_TO_CANONICAL[key];
  }
  if (simple.includes("carcinoma of prostate") || simple.includes("prostate carcinoma")) {
    return "prostate";
  }
  return undefined;
}

function checkItemTags(item) {
  for (const [tag, method] of TAGS_TO_CHECK) {
    const val = method === "codeMeaning" ? getCodeMeaning(item, tag) : getValue(item, tag);
    if (val) {
      const normalized = canonicalizeBodyPart(val);
      if (normalized) return normalized;
    }
  }
  return undefined;
}

// ====== Routes ======

app.get("/api/ping", (_req, res) =>
  res.json({
    ok: true,
    dicomWebFilter: DICOM_WEB_FILTER_URL,
    kaapanaBackend: KAAPANA_BACKEND_URL,
  })
);

// List studies - replaces the frontend's former direct, unauthenticated
// fetch straight to dcm4chee-arc.
app.get("/api/studies", async (req, res) => {
  try {
    const studies = await qidoStudies(req, { fuzzymatching: true, includefield: "all" });
    res.json(studies);
  } catch (err) {
    log("STUDIES: error", err?.response?.data || err?.message || err);
    res.status(500).json({
      error: "Failed to list studies",
      detail: err?.response?.data || err?.message || String(err),
    });
  }
});

// List a study's series - used to resolve the matching SM series once the
// user reveals SLIM for a given radiology study.
app.get("/api/studies/:studyUID/series", async (req, res) => {
  try {
    const series = await qidoSeries(req, req.params.studyUID, { includefield: "all" });
    res.json(series);
  } catch (err) {
    log("SERIES: error", err?.response?.data || err?.message || err);
    res.status(500).json({
      error: "Failed to list series",
      detail: err?.response?.data || err?.message || String(err),
    });
  }
});

// Given a clicked segment's label (from the ohif-segment-click postMessage -
// see Kaapana's customization.patch addition to OHIFCornerstoneSEGViewport.tsx
// and App.jsx's message listener), find the pathology (SM) series for this
// same patient whose own DICOM tags resolve to the same canonical organ.
// Returns {} if nothing matches (or no label was given) - only the specific
// organ a pathology slide actually exists for should be clickable, not every
// segmented organ (no "just show any SM series" fallback here on purpose -
// mirrors kaapana-backend's body_part_matching.find_matching_sm_series).
// GET /api/studies/:studyUID/matching-sm-series?label=<segment label>
app.get("/api/studies/:studyUID/matching-sm-series", async (req, res) => {
  try {
    const { studyUID } = req.params;
    const wantedCanonical = canonicalizeBodyPart(req.query.label);
    if (!wantedCanonical) {
      return res.json({});
    }

    const mr = await qidoStudies(req, { StudyInstanceUID: studyUID, includefield: "all", limit: 1 });
    if (!mr?.length) return res.status(404).json({ error: "Study not found", studyUID });
    const patientID = getValue(mr[0], "00100020");
    if (!patientID) return res.status(404).json({ error: "Study missing PatientID", studyUID });

    const smStudies = await qidoStudies(req, {
      PatientID: patientID,
      ModalitiesInStudy: "SM",
      includefield: "all",
      limit: 10,
    });
    if (!smStudies?.length) {
      log("MATCHING_SM_SERIES: no SM studies for this patient", { studyUID, patientID });
      return res.json({});
    }

    for (const smStudy of smStudies) {
      const smStudyUID = getValue(smStudy, "0020000D");
      const seriesList = await qidoSeries(req, smStudyUID, { includefield: "all" });
      for (const series of seriesList || []) {
        const smSeriesUID = getValue(series, "0020000E");

        let canonical = checkItemTags(smStudy) || checkItemTags(series);
        if (!canonical) {
          const instances = await qidoInstances(req, smStudyUID, smSeriesUID, {
            includefield: "all",
            limit: 1,
          });
          if (instances?.length) canonical = checkItemTags(instances[0]);
        }

        if (canonical === wantedCanonical) {
          return res.json({ smStudyUID, smSeriesUID, matchedBodyPart: canonical });
        }
      }
    }

    log("MATCHING_SM_SERIES: no organ match", { studyUID, label: req.query.label, wantedCanonical });
    return res.json({});
  } catch (err) {
    log("MATCHING_SM_SERIES: error", err?.response?.data || err?.message || err);
    res.status(500).json({
      error: "Failed to find a matching SM series",
      detail: err?.response?.data || err?.message || String(err),
    });
  }
});

// Trigger the auto-segmentation-pipeline DAG instead of running
// TotalSegmentator inline here - this replaces the former ~250-line inline
// pipeline (download study -> dcm2niix -> TotalSegmentator exec -> build
// DICOM SEG -> STOW to PACS) entirely; body-part inference and
// TotalSegmentator v2 execution both already happen properly inside that DAG.
// POST /api/segment/run { studyUID }
app.post("/api/segment/run", async (req, res) => {
  try {
    const { studyUID } = req.body || {};
    if (!studyUID) return res.status(400).json({ error: "studyUID is required" });

    const headers = authHeaders(req);

    // Resolve the study's CT/MR series UID - the DAG's data_form.identifiers
    // needs a series UID, not a study UID (confirmed against real Kaapana
    // trigger conf captured earlier in this project's own task logs).
    const series = await qidoSeries(req, studyUID, { includefield: "all" });
    const ctOrMr = (series || []).find((s) =>
      ["CT", "MR"].includes((getValue(s, "00080060") || "").toUpperCase())
    );
    const seriesUID = ctOrMr ? getValue(ctOrMr, "0020000E") : undefined;
    if (!seriesUID) {
      return res.status(404).json({ error: "No CT/MR series found in this study", studyUID });
    }

    // The local Kaapana instance's id, required by JobCreate - discovered,
    // not hardcoded (services/base/kaapana-backend's GET /client/kaapana-instance,
    // which defaults to the local instance when called with no params).
    const instanceResp = await axios.get(`${KAAPANA_BACKEND_URL}/client/kaapana-instance`, {
      headers,
    });
    const kaapanaInstanceId = instanceResp.data?.id;
    if (!kaapanaInstanceId) {
      return res.status(502).json({ error: "Could not resolve the local Kaapana instance" });
    }

    const projectForm = await resolveProjectForm(req);
    if (!projectForm) {
      return res.status(502).json({ error: "Could not resolve the active project" });
    }

    const jobPayload = {
      dag_id: AUTO_SEGMENTATION_DAG_ID,
      kaapana_instance_id: kaapanaInstanceId,
      username: forwardedUsername(req),
      // Defaults to false in kaapana-backend's JobCreate schema - without this,
      // create_job() only inserts a "queued" row and never actually calls
      // Airflow (see workflows/crud.py's create_job(), which only schedules
      // when automatic_execution is True), so the job sits forever with
      // run_id=null and no DAG run ever appears in Airflow.
      automatic_execution: true,
      conf_data: {
        // GetInputOperator (every DAG's first task) requires this - see
        // resolveProjectForm()'s comment above for why it's not optional.
        project_form: projectForm,
        data_form: { identifiers: [seriesUID] },
        // get_input.py's check_modality_of_workflow() validates the series'
        // actual modality against this comma-separated list - the DAG's own
        // ui_forms declares "input": "CT" as the default a normal UI-driven
        // trigger would send; we support both CT and MR here.
        workflow_form: { input: "CT,MR" },
      },
    };

    const jobResp = await axios.post(`${KAAPANA_BACKEND_URL}/client/job`, jobPayload, { headers });
    log("SEG_RUN: triggered", AUTO_SEGMENTATION_DAG_ID, {
      studyUID,
      seriesUID,
      jobId: jobResp.data?.id,
      runId: jobResp.data?.run_id,
    });

    return res.json({
      status: "ok",
      studyUID,
      seriesUID,
      jobId: jobResp.data?.id,
      runId: jobResp.data?.run_id,
    });
  } catch (err) {
    log("SEG_RUN: error", err?.response?.data || err?.message || err);
    return res.status(500).json({
      error: `Failed to trigger ${AUTO_SEGMENTATION_DAG_ID}`,
      detail: err?.response?.data || err?.message || String(err),
    });
  }
});

// ==== static frontend (built by `npm run build` in the Vite project root) ====
app.use(express.static(path.join(__dirname, "..", "dist")));

// ==== start server ====
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  log(`Split-viewer backend listening on :${PORT}`);
  log(`dicom-web-filter: ${DICOM_WEB_FILTER_URL}`);
  log(`kaapana-backend: ${KAAPANA_BACKEND_URL}`);
});
