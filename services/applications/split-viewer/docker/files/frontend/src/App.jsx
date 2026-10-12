import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Search, ChevronDown, ChevronUp, ArrowLeft, Tv2 } from 'lucide-react';

// --- Configuration ---
// OHIF and SLIM are Kaapana's own already-deployed services, same origin as
// this app (served behind the same Traefik ingress) - no proxying of our own
// needed, unlike the original standalone stack's self-hosted nginx+dcm4chee.
const VIEWERS_CONFIG = {
  ohif: '/ohif/',
  slim: '/slim/',
};

// PACS access goes through this app's own backend (/api/*), which in turn
// talks to dicom-web-filter-service with the caller's forwarded Kaapana auth
// - see server/server.js. Not called directly from the browser so the
// backend can also use it when triggering the auto-segmentation-pipeline DAG.
// Prefixed with Vite's runtime base (import.meta.env.BASE_URL, "/split-viewer/"
// in this chart - see vite.config.js) since Traefik only routes that subpath
// to this pod; a plain "/api/..." fetch would miss the ingress entirely.
const API_BASE = import.meta.env.BASE_URL.replace(/\/$/, '');
const STUDIES_URL = `${API_BASE}/api/studies`;

// --- Reusable Components ---
const SearchInput = ({ value, onChange, placeholder }) => (
  <div className="relative w-full md:w-1/3">
    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
    <input
      type="text"
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-shadow text-black"
    />
  </div>
);

const TableHeader = ({ children, sortable, sorted, direction, onSort, className = '' }) => (
  <th
    className={`p-4 text-left font-semibold text-gray-600 uppercase tracking-wider ${
      sortable ? 'cursor-pointer hover:bg-gray-100' : ''
    } ${className}`}
    onClick={sortable ? onSort : undefined}
  >
    <div className="flex items-center">
      {children}
      {sortable && (
        <span className="ml-2">
          {sorted ? (
            direction === 'asc' ? (
              <ChevronUp size={16} />
            ) : (
              <ChevronDown size={16} />
            )
          ) : (
            <ChevronDown size={16} className="text-gray-300" />
          )}
        </span>
      )}
    </div>
  </th>
);

// --- Split View Component ---
const SplitView = ({ study, onBack }) => {
  const [showSlim, setShowSlim] = useState(false);
  const [splitRatio, setSplitRatio] = useState(50);
  const [clickedSegmentLabel, setClickedSegmentLabel] = useState(null);
  const [smMatch, setSmMatch] = useState(null); // { smStudyUID, smSeriesUID, matchedBodyPart }

  // Real segment-click signal from OHIF itself (see Kaapana's
  // customization.patch addition to OHIFCornerstoneSEGViewport.tsx): OHIF
  // resolves the actual clicked segment via Cornerstone3D's own labelmap/
  // contour hit-testing and posts { type: 'ohif-segment-click', segmentationId,
  // segmentIndex, label } - replaces the previous canvas-pixel-color-guessing
  // approach, which couldn't tell segments apart and only worked by forcing
  // OHIF and this page onto the same origin so its DOM/canvas was readable.
  useEffect(() => {
    const handleMessage = (event) => {
      if (event.data?.type !== 'ohif-segment-click') return;
      setClickedSegmentLabel(event.data.label ?? null);
      setShowSlim(true);
    };
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // When showSlim flips true, find the pathology (SM) series whose own DICOM
  // tags resolve to the same organ as the clicked segment's label - not just
  // "any SM series for this patient". server/server.js's
  // GET /api/studies/:studyUID/matching-sm-series returns {} if nothing
  // matches, so smMatch below simply stays unset and SLIM doesn't open.
  useEffect(() => {
    if (!showSlim) return;

    const params = clickedSegmentLabel ? `?label=${encodeURIComponent(clickedSegmentLabel)}` : '';
    fetch(`${API_BASE}/api/studies/${study.id}/matching-sm-series${params}`)
      .then((r) => r.json())
      .then((match) => {
        if (match?.smStudyUID && match?.smSeriesUID) {
          setSmMatch(match);
        }
      })
      .catch((err) => console.error('Failed to find a matching SM series:', err));
  }, [showSlim, study.id, clickedSegmentLabel]);

  if (!study) return null;

  const ohifUrl = `${VIEWERS_CONFIG.ohif}viewer?StudyInstanceUIDs=${study.id}`;
  const slimUrl =
    smMatch &&
    `${VIEWERS_CONFIG.slim}studies/${smMatch.smStudyUID}/series/${smMatch.smSeriesUID}`;

  return (
    <div className="flex flex-col h-screen bg-gray-800">
      <header className="flex-shrink-0 bg-gray-900 text-white p-3 flex items-center justify-between shadow-lg space-x-4">
        <div className="flex items-center space-x-2 flex-shrink-0">
          <button
            onClick={onBack}
            className="flex items-center rounded-md transition-colors"
            style={{ padding: '8px 16px', background: '#2563eb', color: '#fff', fontWeight: 600, border: 'none', cursor: 'pointer' }}
            onMouseEnter={e => e.currentTarget.style.background = '#1d4ed8'}
            onMouseLeave={e => e.currentTarget.style.background = '#2563eb'}
          >
            <ArrowLeft size={20} className="mr-2" />
            Back
          </button>
          {showSlim && (
            <button
              onClick={() => {
                setShowSlim(false);
                setSmMatch(null);
                setClickedSegmentLabel(null);
              }}
              className="flex items-center rounded-md transition-colors"
              style={{ padding: '8px 16px', background: '#0d9488', color: '#fff', fontWeight: 600, border: 'none', cursor: 'pointer' }}
              onMouseEnter={e => e.currentTarget.style.background = '#0f766e'}
              onMouseLeave={e => e.currentTarget.style.background = '#0d9488'}
            >
              <Tv2 size={20} className="mr-2" />
              Hide SLIM
            </button>
          )}
        </div>

        <div className="flex-grow flex items-center justify-center min-w-0 px-4">
          {showSlim && (
            <input
              type="range"
              min="10"
              max="90"
              value={splitRatio}
              onChange={(e) => setSplitRatio(+e.target.value)}
              className="w-1/2 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer"
              title={`Adjust split (${splitRatio}%)`}
            />
          )}
        </div>

        <div className="text-right flex-shrink-0" style={{ width: '250px' }}>
          <div className="font-semibold text-white truncate">{study.patientName}</div>
          <div className="text-xs text-gray-400">
            <span>ID: {study.patientId}</span>
            <span className="mx-2">|</span>
            <span>Date: {study.studyDate}</span>
          </div>
        </div>
      </header>

      <main className="flex-grow flex w-full h-full overflow-hidden">
        {showSlim && slimUrl && (
          <div className="h-full border-r-2 border-gray-700" style={{ width: `${100 - splitRatio}%` }}>
            <iframe src={slimUrl} title="SLIM Viewer" className="w-full h-full border-0" />
          </div>
        )}
        <div className="h-full transition-all duration-200 ease-in-out" style={{ width: showSlim ? `${splitRatio}%` : '100%' }}>
          <iframe src={ohifUrl} title="OHIF Viewer" className="w-full h-full border-0" />
        </div>
      </main>
    </div>
  );
};

// --- Segmentation Log Modal ---
const SegModal = ({ log, status, studyLabel, onClose }) => {
  const logEndRef = useRef(null);
  useEffect(() => { logEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [log]);

  if (!status) return null;
  const running = status === 'running';
  const done    = status === 'done';

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
      <style>{`@keyframes _spin { to { transform: rotate(360deg); } }`}</style>
      <div style={{ background: '#1a1a2e', borderRadius: '14px', width: '740px', maxWidth: '92vw', maxHeight: '80vh', display: 'flex', flexDirection: 'column', boxShadow: '0 30px 60px rgba(0,0,0,0.6)', border: '1px solid #2d2d4e' }}>

        {/* header bar */}
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #2d2d4e', display: 'flex', alignItems: 'center', gap: '12px', background: '#16213e', borderRadius: '14px 14px 0 0' }}>
          <div style={{ display: 'flex', gap: '6px' }}>
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f57' }} />
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#febc2e' }} />
            <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#28c840' }} />
          </div>
          <span style={{ color: '#8b8baa', fontSize: '13px', fontFamily: 'monospace', flex: 1, textAlign: 'center' }}>
            TotalSegmentator — {studyLabel}
          </span>
          {running
            ? <div style={{ width: 18, height: 18, border: '2px solid #4f6ef7', borderTopColor: 'transparent', borderRadius: '50%', animation: '_spin 0.8s linear infinite' }} />
            : <button onClick={onClose} style={{ background: 'transparent', border: '1px solid #444', color: '#aaa', borderRadius: '6px', padding: '2px 10px', cursor: 'pointer', fontSize: '13px' }}>Close</button>
          }
        </div>

        {/* status badge */}
        <div style={{ padding: '8px 20px', background: '#0f3460', display: 'flex', alignItems: 'center', gap: '8px' }}>
          {running && <span style={{ color: '#60a5fa', fontSize: '13px', fontWeight: 600 }}>● Running…</span>}
          {done    && <span style={{ color: '#4ade80', fontSize: '13px', fontWeight: 600 }}>✔ Completed</span>}
          {status === 'error' && <span style={{ color: '#f87171', fontSize: '13px', fontWeight: 600 }}>✘ Failed</span>}
        </div>

        {/* log output */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', fontFamily: "'Menlo','Monaco','Consolas',monospace", fontSize: '13px', lineHeight: '1.6', color: '#c8d3f5', background: '#1a1a2e' }}>
          {log.map((line, i) => {
            const isErr  = /error|fail|exception/i.test(line);
            const isWarn = /warn/i.test(line);
            const isDone = /✔|success|complet/i.test(line);
            const color  = isErr ? '#f87171' : isWarn ? '#fbbf24' : isDone ? '#4ade80' : '#c8d3f5';
            return (
              <div key={i} style={{ color, paddingBottom: '1px' }}>
                <span style={{ color: '#4f6ef7', userSelect: 'none' }}>{'>'} </span>{line}
              </div>
            );
          })}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
};

// --- Study List Component ---
const StudyList = ({ studies, onSelectStudy }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'studyDate', direction: 'desc' });
  const [busyUID, setBusyUID] = useState(null);
  const [segLog, setSegLog] = useState([]);
  const [segStatus, setSegStatus] = useState(null); // null | 'running' | 'done' | 'error'
  const [segLabel, setSegLabel] = useState('');

  const getStudyUID = (study) => study?.id ?? null;

  const handleSort = (key) => {
    let direction = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') direction = 'desc';
    setSortConfig({ key, direction });
  };

  const appendLog = (line) => setSegLog((prev) => [...prev, line]);

  const runSegmentation = async (study) => {
    const studyUID = getStudyUID(study);
    if (!studyUID) {
      setSegLog(['Error: Missing StudyInstanceUID for this study.']);
      setSegStatus('error');
      return;
    }

    setSegLog([`Triggering auto-segmentation-pipeline for study ${studyUID} …`]);
    setSegStatus('running');
    setSegLabel(study.patientId || studyUID);
    setBusyUID(studyUID);

    // This only triggers the DAG (via the backend's own POST /client/job call -
    // see server/server.js) and returns immediately; it doesn't wait for or
    // stream the run's actual progress the way the original inline
    // TotalSegmentator pipeline's log did. Full progress/logs are visible in
    // Kaapana's own Workflow Execution UI for this job/run id.
    try {
      const resp = await fetch(`${API_BASE}/api/segment/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ studyUID }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data?.detail || data?.error || `Request failed (${resp.status})`);

      appendLog(`Series    : ${data?.seriesUID || 'unknown'}`);
      appendLog(`Job id    : ${data?.jobId ?? 'unknown'}`);
      appendLog(`Run id    : ${data?.runId || 'unknown'}`);
      appendLog('✔ auto-segmentation-pipeline triggered - see Kaapana Workflow Execution for progress.');
      setSegStatus('done');
    } catch (e) {
      console.error(e);
      appendLog(`✘ ${e.message}`);
      setSegStatus('error');
    } finally {
      setBusyUID(null);
    }
  };

  const sortedAndFilteredStudies = useMemo(() => {
    return [...studies]
      .filter((study) =>
        Object.values(study).some((v) => String(v).toLowerCase().includes(searchTerm.toLowerCase()))
      )
      .sort((a, b) => {
        if (!sortConfig.key) return 0;
        if (a[sortConfig.key] < b[sortConfig.key]) return sortConfig.direction === 'asc' ? -1 : 1;
        if (a[sortConfig.key] > b[sortConfig.key]) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
      });
  }, [studies, searchTerm, sortConfig]);

  return (
    <div className="bg-gray-50 min-h-screen font-sans">
      <SegModal
        log={segLog}
        status={segStatus}
        studyLabel={segLabel}
        onClose={() => setSegStatus(null)}
      />
      <div className="w-full p-4 md:p-8">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-gray-800">Split-Viewer: Study List</h1>
          <p className="text-gray-500 mt-1">Viewing studies from local DCM4CHEE server.</p>
        </header>

        <div className="bg-white rounded-xl shadow-md overflow-hidden">
          <div className="p-4 md:p-6 border-b border-gray-200 flex justify-between items-center">
            <SearchInput value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} placeholder="Search studies..." />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <TableHeader>Patient ID</TableHeader>
                  <TableHeader>Patient Name</TableHeader>
                  <TableHeader>Study Date</TableHeader>
                  <TableHeader>Modality</TableHeader>
                  <TableHeader>Description</TableHeader>
                  <TableHeader>Actions</TableHeader>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sortedAndFilteredStudies.map((s) => {
                  const isBusy = busyUID === s.id;
                  return (
                    <tr key={s.id} className="hover:bg-gray-50 transition-colors">
                      <td className="p-4 whitespace-nowrap text-sm font-medium text-gray-800">{s.patientId}</td>
                      <td className="p-4 whitespace-nowrap text-sm text-gray-600">{s.patientName}</td>
                      <td className="p-4 whitespace-nowrap text-sm text-gray-600">{s.studyDate}</td>
                      <td className="p-4 whitespace-nowrap text-sm">
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                          {s.modality}
                        </span>
                      </td>
                      <td className="p-4 text-sm text-gray-600 max-w-xs truncate">{s.description}</td>
                      <td className="p-4 whitespace-nowrap text-sm font-medium" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <button
                          onClick={() => onSelectStudy(s)}
                          style={{ padding: '5px 14px', background: '#16a34a', color: '#fff', fontWeight: 600, fontSize: '13px', border: 'none', borderRadius: '6px', cursor: 'pointer', boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }}
                          onMouseEnter={e => e.currentTarget.style.background = '#15803d'}
                          onMouseLeave={e => e.currentTarget.style.background = '#16a34a'}
                        >
                          Open Viewer
                        </button>
                        <button
                          onClick={() => runSegmentation(s)}
                          disabled={isBusy}
                          title="Run TotalSegmentator and create DICOM SEG"
                          style={{ padding: '5px 14px', background: isBusy ? '#9ca3af' : '#059669', color: '#fff', fontWeight: 600, fontSize: '13px', border: 'none', borderRadius: '6px', cursor: isBusy ? 'not-allowed' : 'pointer', boxShadow: '0 1px 3px rgba(0,0,0,0.2)' }}
                          onMouseEnter={e => { if (!isBusy) e.currentTarget.style.background = '#047857'; }}
                          onMouseLeave={e => { if (!isBusy) e.currentTarget.style.background = '#059669'; }}
                        >
                          {isBusy ? 'Running…' : 'Segment (TS)'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
        <footer className="text-center mt-8 text-gray-400 text-sm">
          <p>Designed by Nilesh Parshotam Rijhwani (C140)</p>
        </footer>
      </div>
    </div>
  );
};

// --- Main App Component ---
export default function App() {
  const [studies, setStudies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentView, setCurrentView] = useState('list');
  const [selectedStudy, setSelectedStudy] = useState(null);

  const formatDicomDate = (dicomDate) => {
    if (!dicomDate || dicomDate.length !== 8) return 'N/A';
    return `${dicomDate.slice(0, 4)}-${dicomDate.slice(4, 6)}-${dicomDate.slice(6, 8)}`;
  };

  useEffect(() => {
    const fetchStudies = async () => {
      setLoading(true);
      try {
        // fuzzymatching/includefield are applied server-side (server/server.js)
        const res = await fetch(STUDIES_URL);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const formatted = data.map((st) => {
          const getValue = (tag, def = 'N/A') => st[tag]?.Value?.[0] ?? def;
          return {
            id: getValue('0020000D'),
            patientId: getValue('00100020'),
            patientName: getValue('00100010')?.Alphabetic ?? 'N/A',
            studyDate: formatDicomDate(getValue('00080020')),
            modality: getValue('00080061'),
            description: getValue('00081030'),
          };
        });
        setStudies(formatted);
      } catch (e) {
        console.error(e);
        setError('Failed to fetch studies. Check console and DCM4CHEE server.');
      } finally {
        setLoading(false);
      }
    };
    fetchStudies();
  }, []);

  const handleSelectStudy = (st) => {
    setSelectedStudy(st);
    setCurrentView('split');
  };
  const handleBackToList = () => {
    setSelectedStudy(null);
    setCurrentView('list');
  };

  if (loading) return <div className="flex items-center justify-center h-screen">Loading...</div>;
  if (error) return <div className="flex items-center justify-center h-screen text-red-500">{error}</div>;
  if (currentView === 'split')
    return <SplitView study={selectedStudy} onBack={handleBackToList} />;
  return <StudyList studies={studies} onSelectStudy={handleSelectStudy} />;
}
