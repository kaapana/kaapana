<template>
    <v-row>
        <v-col>
            <v-row justify="space-between">
                <v-col cols="6">
                    <div class="d-flex align-center gap-2">
                        <v-btn v-if="!expanded" icon="mdi-chevron-right" color="primary" variant="text"
                            @click="toggleExpand">
                        </v-btn>
                        <v-btn v-if="expanded" icon="mdi-chevron-down" color="primary" variant="text"
                            @click="toggleExpand">
                        </v-btn>
                        <h5 class="text-h5 py-4">Executable Workflows</h5>
                    </div>
                </v-col>
                <v-col cols="4" class="d-flex justify-end align-center">
                    <v-btn block @click="onAddWorkflowClick" size="large" prepend-icon="mdi-gamepad-variant"
                        min-width="300" v-if="userHasAdminAccess || can(project?.id, 'manage_project_software')">
                        Add executable workflow to project
                    </v-btn>
                </v-col>
            </v-row>
            <v-data-table v-if="allowedSoftware.length > 0 && expanded" :headers="softwareTableHeaders"
                :items="allowedSoftware"
                :sort-by="[{ key: 'software_uuid', order: 'asc' }]" multi-sort>
                <template #item="{ item }">
                    <tr>
                        <td><v-icon>mdi-gamepad-variant</v-icon></td>
                        <td>{{ item.software_uuid }}</td>
                        <td class="text-center"
                            v-if="userHasAdminAccess || can(project?.id, 'manage_project_software')">
                            <v-btn @click="onDeleteSoftware(item.software_uuid)" density="default"
                                icon="mdi-trash-can"></v-btn>
                        </td>
                    </tr>
                </template>
            </v-data-table>
            <v-sheet rounded v-if="allowedSoftware.length == 0 && expanded">
                <v-container>
                    <v-row align="center" justify="center" no-gutters>
                        <v-icon icon="mdi-information" size="x-large" class="large-font"></v-icon>
                    </v-row>
                    <v-row align="center" justify="center" no-gutters class="py-6">
                        <div class="text-subtitle-1 font-weight-light text-center">
                            No DAG allowed for this Project. Click the following button to allow a DAG.
                        </div>
                    </v-row>
                    <v-row align="center" justify="center" no-gutters>
                        <v-btn @click="onAddWorkflowClick" size="large" variant="outlined"
                            prepend-icon="mdi-gamepad-variant">
                            Add DAG to project
                        </v-btn>
                    </v-row>
                </v-container>
            </v-sheet>
        </v-col>
    </v-row>
</template>

<script lang="ts" setup>
import { computed } from 'vue';
import { Software } from '@/common/types';
import { usePermissions } from '@/permissions/usePermissions';

interface Props {
    project: { id?: string };
    allowedSoftware: Software[];
    expanded: boolean;
    userHasAdminAccess: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits(['toggle', 'add-workflow', 'delete-software']);

const { can } = usePermissions();

const toggleExpand = () => {
    emit('toggle', !props.expanded);
};

const onAddWorkflowClick = () => {
    emit('add-workflow');
};

const onDeleteSoftware = (softwareUuid: string) => {
    emit('delete-software', softwareUuid);
};

const softwareTableHeaders = [
    { title: '', key: 'icon', width: '40px' },
    { title: 'Workflow ID', key: 'software_uuid' },
    { title: '', key: 'actions', align: 'center' as const, width: '60px' }
];
</script>

<style scoped>
.large-font {
    font-size: 40px;
}
</style>
