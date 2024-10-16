<template>
    <v-container max-width="1200">
        <v-row justify="space-between">
            <v-col cols="6">
                <h4 class="text-h4 py-8">Project {{ projectId }}</h4>
                <p v-if="details">{{ details.description }}</p>
            </v-col>
        </v-row>
        <v-row>
            <v-col>
                <v-row justify="space-between">
                    <v-col cols="6">
                        <h5 class="text-h5 py-4">Project Users</h5>
                    </v-col>
                    <v-col cols="3" class="d-flex justify-end align-center">
                        <v-btn block @click="userDialog = true" size="large" prepend-icon="mdi-account-plus">
                            Add User to Project
                        </v-btn>
                    </v-col>
                </v-row>
                <v-table>
                    <thead>
                        <tr>
                            <th></th>
                            <th class="text-left">
                                Username
                            </th>
                            <th class="text-left">
                                First Name
                            </th>
                            <th class="text-left">
                                Last Name
                            </th>
                            <th class="text-left">
                                Verified Email
                            </th>
                            <th class="text-left">
                                Role
                            </th>
                            <th class="text-center">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="item in users" :key="item.username">
                            <td><v-icon>mdi-account-circle</v-icon></td>
                            <td>{{ item.username }}</td>
                            <td>{{ item.first_name }}</td>
                            <td>{{ item.last_name }}</td>
                            <td>{{ item.email_verified }}</td>
                            <td>{{ item.role?.name }}</td>
                            <td class="text-right">
                                <v-btn @click="openUserEditDialog(item)" density="default"
                                    icon="mdi-link-edit"></v-btn>
                                <v-btn @click="deleteUserProjectMapping(item.id)" density="default"
                                    icon="mdi-trash-can"></v-btn>
                            </td>
                        </tr>
                    </tbody>
                </v-table>
            </v-col>
        </v-row>
    </v-container>
    <v-dialog v-model="userDialog" max-width="1000">
        <AddUserToProject :project-name="projectId" :current-user-ids="userIds" :onsuccess="handleUserAdd"
            :oncancel="() => userDialog = false" />
    </v-dialog>
    <v-dialog v-model="userEditDialog" max-width="1000">
        <AddUserToProject :project-name="projectId" action-type="update" :selected-user="selectedUser" :onsuccess="handleUserAdd"
            :oncancel="() => userEditDialog = false" />
    </v-dialog>
    <confirm ref="confirm"></confirm>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { aiiApiGet, aiiApiDelete } from '@/common/aiiApi.service'
import { ProjectItem, UserItem, UserRole } from '@/common/types'
import AddUserToProject from '@/components/AddUserToProject.vue'

// const route = useRoute()

interface User extends UserItem {
    role?: UserRole
}

export default defineComponent({
    components: {
        AddUserToProject
    },
    props: {},
    data() {
        return {
            projectId: this.$route.params.id as string, // Access the route param
            details: null as ProjectItem | null,
            users: [] as User[],
            userDialog: false,
            userIds: [] as string[],
            userEditDialog: false,
            selectedUser: undefined as UserItem | undefined,
        };
    },
    mounted() {
        this.fetchProjectDetails();
        this.fetchProjectUsers();
    },
    watch: {
        // Watch the route to handle dynamic changes to the route param
        '$route.params.id': function (newProjectID) {
            this.projectId = newProjectID;
        },
        'users': function (newUsers: User[]) {
            let tempUserIds: string[] = []
            newUsers.forEach((user, index) => {
                this.fetchProjectUserRole(user.id, index);
                tempUserIds.push(user.id);
            });
            this.userIds = [...tempUserIds];
        }
    },
    methods: {
        handleUserAdd(success: boolean = true) {
            if (success) {
                this.fetchProjectUsers();
            }
            this.userDialog = false;
            this.userEditDialog = false;
        },
        async deleteUserProjectMapping(userId: string) {
            if (await this.$refs.confirm.open('Delete User from Project', 'Are you sure?', { color: 'red' })) {
                this.deleteProjectUsers(userId);
            }
        },
        openUserEditDialog(selectedUser: UserItem) {
            this.selectedUser = selectedUser;
            this.userEditDialog = true;
        },
        fetchProjectDetails() {
            if (this.projectId) {
                try {
                    aiiApiGet(`projects/${this.projectId}`).then((project: ProjectItem) => {
                        this.details = project;
                    })
                } catch (error: unknown) {
                    console.log(error);
                }
            }
        },
        fetchProjectUsers() {
            if (this.projectId) {
                try {
                    aiiApiGet(`projects/${this.projectId}/users`).then((users: UserItem[]) => {
                        this.users = users;
                    })
                } catch (error: unknown) {
                    console.log(error);
                }
            }
        },
        fetchProjectUserRole(userId: string, userIdx: number) {
            if (this.projectId) {
                try {
                    aiiApiGet(`projects/${this.projectId}/users/${userId}/roles`).then((role: UserRole) => {
                        this.users[userIdx].role = role
                    })
                } catch (error: unknown) {
                    console.log(error);
                }
            }
        },
        deleteProjectUsers(userId: string) {
            if (this.projectId) {
                try {
                    aiiApiDelete(`projects/${this.projectId}/user/${userId}/rolemapping`).then((success: boolean) => {
                        if (success) {
                            this.fetchProjectUsers();
                        }
                    })
                } catch (error: unknown) {
                    console.log(error);
                }
            }
        },
    }
})
</script>