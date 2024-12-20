<template>
    <v-container max-width="1200">
        <v-row no-gutters>
            <v-btn size="x-small" variant="outlined" prepend-icon="mdi-arrow-left" @click="goToProjectsList">Back</v-btn>
        </v-row>
        <v-row justify="space-between">
            <v-col>
                <h4 class="text-h4 pb-8">
                    <v-btn class="ma-2" icon="mdi-folder-file" fab readonly></v-btn>
                    Project {{ projectId }}
                </h4>
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
                        <v-btn block @click="userDialog = true" size="large" prepend-icon="mdi-account-plus" v-if="userHasAdminAccess">
                            Add User to Project
                        </v-btn>
                    </v-col>
                </v-row>
                <v-table v-if="users.length > 0">
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
                            <th class="text-center" v-if="userHasAdminAccess">
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
                            <td class="text-right" v-if="userHasAdminAccess">
                                <v-btn @click="openUserEditDialog(item)" density="default" icon="mdi-link-edit"></v-btn>
                                <v-btn @click="deleteUserProjectMapping(item.id)" density="default"
                                    icon="mdi-trash-can"></v-btn>
                            </td>
                        </tr>
                    </tbody>
                </v-table>
                <v-sheet rounded v-else-if="!fetchingUser">
                    <v-container>
                        <v-row align="center" justify="center" no-gutters>
                            <v-icon icon="mdi-information" size="x-large" class="large-font"</v-icon>
                        </v-row>
                        <v-row align="center" justify="center" no-gutters class="py-6">                            
                            <div class="text-subtitle-1 font-weight-light text-center">
                                No User found under this Project. Click the following button to Add new user.
                            </div>
                        </v-row>
                        <v-row align="center" justify="center" no-gutters>
                            <v-btn @click="userDialog = true" size="large" variant="outlined" prepend-icon="mdi-account-plus">
                                Add User to Project
                            </v-btn>
                        </v-row>
                    </v-container>
                </v-sheet>
            </v-col>
        </v-row>
    </v-container>
    <v-dialog v-model="userDialog" max-width="1000">
        <AddUserToProject :project-name="projectId" :current-user-ids="userIds" :onsuccess="handleUserSubmit"
            :oncancel="resetUserFormValues" />
    </v-dialog>
    <v-dialog v-model="userEditDialog" max-width="1000">
        <AddUserToProject :project-name="projectId" action-type="update" :selected-user="selectedUser"
            :current-role="selectedUser?.role" :onsuccess="handleUserSubmit" :oncancel="resetUserFormValues" />
    </v-dialog>
    <confirm ref="confirm"></confirm>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { aiiApiGet, aiiApiDelete } from '@/common/aiiApi.service'
import { ProjectItem, UserItem, UserRole } from '@/common/types'
import AddUserToProject from '@/components/AddUserToProject.vue'
import store from "@/common/store";

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
            // @ts-ignore
            projectId: this.$route.params.id as string, // Access the route param
            details: null as ProjectItem | null,
            users: [] as User[],
            userDialog: false,
            userIds: [] as string[],
            fetchingUser: false,
            userEditDialog: false,
            selectedUser: undefined as User | undefined,
            userHasAdminAccess: false,
        };
    },
    mounted() {
        this.fetchProjectDetails();
        this.fetchProjectUsers();
        
        // set the userAdminAccess by watching the changes in store user
        const setAdminAccessRef = this.setUserAdminAccess;
        let checkForUser = setInterval(function () {
            const user = store.state.user;
            if (user) {
                setAdminAccessRef(user);
                clearInterval(checkForUser);
            }
        }, 100);
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
        handleUserSubmit(success: boolean = true) {
            if (success) {
                this.fetchProjectUsers();
            }
            this.resetUserFormValues();
        },
        async deleteUserProjectMapping(userId: string) {
            // @ts-ignore
            if (await this.$refs.confirm.open('Delete User from Project', 'Are you sure?', { color: 'red' })) {
                this.deleteProjectUsers(userId);
            }
        },
        openUserEditDialog(selectedUser: User) {
            this.selectedUser = selectedUser;
            this.userEditDialog = true;
        },
        resetUserFormValues() {
            this.userDialog = false;
            this.userEditDialog = false;

            this.selectedUser = undefined;
        },
        // enable the admin access of the user to be able to create new projects from the UI
        setUserAdminAccess(user: UserItem) {
            if (user.realm_roles && (user.realm_roles.includes('project-manager') || user.realm_roles.includes('admin'))) {
                this.userHasAdminAccess = true;
            }
        },
        goToProjectsList() {
            this.$router.push(`/`);
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
                this.fetchingUser = true;
                try {
                    aiiApiGet(`projects/${this.projectId}/users`).then((users: UserItem[]) => {
                        this.users = users;
                        this.fetchingUser = false;
                    })
                } catch (error: unknown) {
                    console.log(error);
                    this.fetchingUser = false;
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

<style scoped>
.large-font{
    font-size: 40px;
}
</style>