<template>
    <v-card prepend-icon="mdi-account-plus" title="Add User to Project">
        <v-overlay v-model="fetching" class="align-center justify-center" contained>
            <v-progress-circular color="primary" indeterminate></v-progress-circular>
        </v-overlay>

        <v-card-text>
            <v-container>
                <v-row><v-text-field v-model="projectNameVal" label="Project Name" disabled
                        required></v-text-field></v-row>
                <!-- <v-row><v-text-field v-model="userId" label="User ID"></v-text-field></v-row> -->
                <v-row>
                    <v-select v-model="userId" label="User" :disabled="actionType == 'update'" :items="users" item-title="username" item-value="id"/>
                </v-row>
                <v-row>
                    <v-select v-model="roleName" label="User Role" :items="roles" item-title="name" placeholder="Select a Role"/>
                </v-row>
            </v-container>
        </v-card-text>
        <v-card-actions>
            <v-container>
                <v-row>
                    <v-col cols="6">
                        <v-btn color="surface-variant" size="large" variant="elevated" block
                            @click="cancel">Cancel</v-btn>
                    </v-col>
                    <v-col cols="6">
                        <v-btn :disabled="!valid" color="success" size="large" variant="elevated" block
                            @click="submit">{{ actionType == 'update' ? 'Update' : 'Create' }}</v-btn>
                    </v-col>
                </v-row>
            </v-container>
        </v-card-actions>
    </v-card>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue';
import { aiiApiPost, aiiApiGet, aiiApiPut } from '@/common/aiiApi.service';
import { UserRole, UserItem } from '@/common/types';
import { PropType } from 'vue';


const props = defineProps({
    projectName: {
        type: String,
        required: true,
    },
    projectId: {
        type: String,
        required: true,
    },
    actionType: {
        type: String,
        default: 'add',
    },
    selectedUser: {
        type: Object as PropType<UserItem>,
    },
    currentRole: {
        type: Object as PropType<UserRole>,
    },
    currentUserIds: {
        type: Array<string>,
    },
    oncancel: {
        type: Function,
    },
    onsuccess: {
        type: Function,
    }
});

const projectNameVal = ref(props.projectName);
const roleName = ref('');
const userId = ref('');
const roles = ref<UserRole[]>([])
const users = ref<UserItem[]>([])
const fetching = ref(false)

const valid = computed(() => {
    return ((props.projectName.trim() !== '') && (roleName.value.trim() !== '') && (userId.value.trim() !== ''));
})

onMounted(async () => {
    if (props.selectedUser) {
        userId.value = props.selectedUser.id;
    }

    if (props.actionType !== 'update') {
        fetchAllUsers();
    } else if(props.selectedUser){
        users.value = [props.selectedUser]
    }

    fetchAllRoles();
    if (props.currentRole) {
        roleName.value = props.currentRole.name
    }
})

const fetchAllRoles = async () => {
    fetching.value = true;
    try {
        const fetchedRoles: UserRole[] = await aiiApiGet(`projects/roles`);
        fetching.value = false;
        roles.value = [...fetchedRoles];
    } catch (error: unknown) {
        fetching.value = false;
    }
}

const fetchAllUsers = async () => {
    fetching.value = true;

    // filter current users of the project
    let filterUsers: string[] = [];
    if (props.currentUserIds) {
        filterUsers = [...props.currentUserIds]
    }

    try {
        const fetchedUsers: UserItem[] = await aiiApiGet(`users`);
        fetching.value = false;
        let filteredUser = fetchedUsers.filter((newUser) => !filterUsers.includes(newUser.id))
        users.value = [...filteredUser];
    } catch (error: unknown) {
        fetching.value = false;
    }
}

const submit = async () => {
    // console.log(props.projectName, roleName.value, userId.value);
    const data = {
        "project_id": props.projectId.trim(),
        "role_name": roleName.value.trim(),
        "user_id": userId.value.trim()
    }
    fetching.value = true;

    if (props.actionType == 'update') {
        updateNewUserProjectMap(data);
    } else {
        addNewUserProjectMap(data);
    }
}

const cancel = () => {
    props.oncancel?.();
}

const addNewUserProjectMap = async(data: any) => {
    try {
        await aiiApiPost(`projects/${data['project_id']}/role/${data['role_name']}/user/${data['user_id']}`, {});
        fetching.value = false;
        props.onsuccess?.();
    } catch (error: unknown) {
        fetching.value = false;
        props.onsuccess?.(false);       
    }
}

const updateNewUserProjectMap = async(data: any) => {
    const params = {
        "role_name": data['role_name'],
    }

    try {
        await aiiApiPut(`projects/${data['project_id']}/user/${data['user_id']}/rolemapping`, params);
        fetching.value = false;
        props.onsuccess?.();
    } catch (error: unknown) {
        fetching.value = false;
        props.onsuccess?.(false);       
    }
}

</script>