
const settings = {
    darkMode: true,
    navigationMode: false,
    landingPage: ['Patient Sex', 'Modality'],
    datasets: {
        structured: false,
        cols: 'auto',
        cardText: true,
        tagBar: {
            multiple: false,
            tags: [] as string[]

        },
        itemsPerPagePagination: 1000,
        sort: "00000000 TimestampArrived_datetime",
        sortDirection: "desc",
        executeSlicedSearch: false,
        props: [
            {
                name: 'Series Description',
                display: true,
                truncate: true,
                dashboard: false,
                patientView: false,
                studyView: false
            },
            {
                name: 'Patient ID',
                display: false,
                truncate: true,
                dashboard: false,
                patientView: false,
                studyView: false
            },
            {
                name: 'Patient Name',
                display: true,
                truncate: true,
                dashboard: false,
                patientView: true,
                studyView: false
            },
            {
                name: 'Patient Birth Date',
                display: false,
                truncate: true,
                dashboard: false,
                patientView: true,
                studyView: false
            },
            {
            name: 'Patient Sex',
                display: true,
                truncate: true,
                dashboard: false,
                patientView: true,
                studyView: false
            },
            {
                name: 'Study Description',
                display: true,
                truncate: true,
                dashboard: false,
                patientView: false,
                studyView: false
            },
            {
                name: 'Study Date',
                display: true,
                truncate: true,
                dashboard: false,
                patientView: false,
                studyView: true
            },
            {
                name: 'Modality',
                display: false,
                truncate: false,
                dashboard: true,
                patientView: true,
                studyView: true
            },
            {
                name: 'Tags',
                display: false,
                truncate: false,
                dashboard: true,
                patientView: false,
                studyView: false
            },
            {
                name: 'Manufacturer',
                display: false,
                truncate: false,
                dashboard: true,
                patientView: false,
                studyView: false
            }
        ]
    },
    workflows: {
        /* Per-dag form defaults:
           [dagName]: { properties: { [param]: value }, hideOnUI: [param, ...] }
           hideOnUI params are hidden on the workflow form. */
        validateDicoms: {
            properties: {
                validator_algorithm: 'dciodvfy',
                exit_on_error: false,
                tags_whitelist: [] as string[],
            },
            hideOnUI: ['tags_whitelist'],
        },
    },
}
export type DatasetProp = {
    name: string
    display: boolean
    truncate: boolean
    dashboard: boolean
    patientView: boolean
    studyView: boolean
}
export type Settings = typeof settings

// The shell seeds localStorage["settings"]; served standalone or on a fresh
// profile nothing is there, and a bare JSON.parse(undefined) blanked the view.
// Returns `any`: datasets.cols is number | 'auto', which `Settings` can't express.
function readSettings(): any {
    try {
        const stored = JSON.parse(localStorage['settings'])
        if (stored) return stored
    } catch {
        // absent or malformed -- fall through to the defaults
    }
    // A COPY of the full defaults (components dereference settings.datasets.*):
    // mutate-and-persist callers must not write through to the shared module
    // object. JSON clone because the build target (chrome87) lacks structuredClone.
    return JSON.parse(JSON.stringify(settings))
}

export {settings, readSettings}