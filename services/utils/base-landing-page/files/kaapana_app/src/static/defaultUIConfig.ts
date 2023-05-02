
const settings = {
    darkMode: true,
    navigationMode: false,
    datasets: {
        structured: false,
        cols: 'auto',
        cardText: true,
        tagBar: {
            multiple: false,
            tags: []
        },
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
    }
}
export {settings}