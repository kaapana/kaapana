import type { CleanupStatus } from '@/types/schemas'

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
        case 'Upstream Failed':
            return 'deep-orange'
        case 'Canceled':
            return 'orange' // deep-orange-darken-2
        default:
            return 'grey'
    }
}

export function cleanupStatusColor(status: CleanupStatus): string {
    switch (status) {
        case 'pending':
            return 'blue-grey'
        case 'running':
            return 'blue'
        case 'cleaned':
            return 'green'
        case 'failed':
            return 'red'
        default:
            return 'grey'
    }
}

export function cleanupStatusLabel(status: CleanupStatus): string {
    switch (status) {
        case 'pending':
            return 'Cleanup pending'
        case 'running':
            return 'Cleaning'
        case 'cleaned':
            return 'Cleaned'
        case 'failed':
            return 'Cleanup failed'
        default:
            return ''
    }
}

export default statusColor
