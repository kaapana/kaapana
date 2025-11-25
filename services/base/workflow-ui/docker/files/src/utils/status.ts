export function statusColor(status: string) {
    switch (status) {
        case 'Created':
            return 'grey'
        case 'Running':
            return 'blue'
        case 'Scheduled':
            return 'blue-grey'
        case 'Pending':
            return 'grey-darken-2'
        case 'Completed':
            return 'green'
        case 'Error':
            return 'red'
        case 'Canceled':
            return 'orange' // deep-orange-darken-2
        default:
            return 'grey'
    }
}

export default statusColor
