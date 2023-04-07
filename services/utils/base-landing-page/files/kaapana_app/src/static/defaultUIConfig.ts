
const settings = {
    darkMode: false,
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
                name: 'Patient ID',
                display: true,
                truncate: true,
                dashboard: false
            },
            {
                name: 'Study Description',
                display: true,
                truncate: true,
                dashboard: false
            },
            {
                name: 'Study Date',
                display: true,
                truncate: true,
                dashboard: false
            },
            {
                name: 'Modality',
                display: false,
                truncate: false,
                dashboard: true
            },
            {
                name: 'tags',
                display: false,
                truncate: false,
                dashboard: true
            },
            {
                name: 'Manufacturer',
                display: false,
                truncate: false,
                dashboard: true
            }
        ]
    }
}
export {settings}