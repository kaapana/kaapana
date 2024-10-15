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
                    <v-select v-model="userId" label="User" :items="users" item-title="username" item-value="id"/>
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
                            @click="submit">Submit</v-btn>
                    </v-col>
                </v-row>
            </v-container>
        </v-card-actions>
    </v-card>
</template>

<script lang="ts" setup>
import { ref, computed, onMounted } from 'vue';
import { aiiApiPost, aiiApiGet } from '@/common/aiiApi.service';
import { UserRole, UserItem } from '@/common/types';
import store from '@/common/store';
// import {AxiosError} from axios;



const props = defineProps({
    projectName: {
        type: String,
        required: true,
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
    fetchAllRoles();
    fetchAllUsers();
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
    const user = store.state.user;

    let filterUsers: string[] = [];
    if (user) {
        filterUsers.push(user.id)
    }
    if (props.currentUserIds) {
        filterUsers = [...filterUsers, ...props.currentUserIds]
    }

    console.log(filterUsers);

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
        "project_name": props.projectName.trim(),
        "role_name": roleName.value.trim(),
        "user_id": userId.value.trim()
    }
    fetching.value = true;

    try {
        await aiiApiPost(`projects/${data['project_name']}/role/${data['role_name']}/user/${data['user_id']}`, {});
        fetching.value = false;
        props.onsuccess?.();
    } catch (error: unknown) {
        fetching.value = false;
        props.onsuccess?.(false);       
    }
}

const cancel = () => {
    props.oncancel?.();
}

</script>