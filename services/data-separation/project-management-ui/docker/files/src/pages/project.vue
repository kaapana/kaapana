<template>
    <v-container max-width="1200">
        <v-row no-gutters>
            <v-btn size="x-small" variant="outlined" prepend-icon="mdi-arrow-left"
                @click="goToProjectsList">Back</v-btn>
        </v-row>
        <v-row justify="space-between">
            <v-col>
                <h4 v-if="project" class="text-h4 pb-8">
                    <v-btn class="ma-2" icon="mdi-card" fab readonly></v-btn>
                    Project {{ project.name }}
                </h4>
                <p v-if="project">{{ project.description }}</p>
                <v-skeleton-loader v-else :loading="!project" type="heading, paragraph" />
            </v-col>
        </v-row>
        <v-row>
            <v-col>
                <v-row justify="space-between">
                    <v-col cols="6">
                        <div class="d-flex align-center gap-2">
                            <v-btn v-if="extendProjectUsers == false" icon="mdi-chevron-right" @click="extendProjectUsers = true">
                            </v-btn>
                            <v-btn v-if="extendProjectUsers == true" icon="mdi-chevron-down" @click="extendProjectUsers = false">
                            </v-btn>
                            <h5 class="text-h5 py-4">Project Users</h5>
                        </div>
                    </v-col>
                    <v-col cols="3" class="d-flex justify-end align-center">
                        <v-btn 
                            block 
                            @click="userDialog = true" 
                            size="large"
                            min-width="260"
                            prepend-icon="mdi-account-plus"
                            v-if="userHasAdminAccess || can(project?.id,'manage_project_users')">
                            Add User to Project
                        </v-btn>
                    </v-col>
                </v-row>
                <v-table v-if="users.length > 0 && extendProjectUsers == true">
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
                            <th class="text-center" v-if="userHasAdminAccess || can(project?.id,'manage_project_users')">
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
                            <td class="text-right" v-if="userHasAdminAccess || can(project?.id,'manage_project_users')">
                                <v-btn @click="openUserEditDialog(item)" density="default" icon="mdi-link-edit"></v-btn>
                                <v-btn @click="deleteUserProjectMapping(item.id)" density="default"
                                    icon="mdi-trash-can"></v-btn>
                            </td>
                        </tr>
                    </tbody>
                </v-table>
                <v-sheet rounded v-else-if="!fetchingUser && extendProjectUsers == true">
                    <v-container>
                        <v-row align="center" justify="center" no-gutters>
                            <v-icon icon="mdi-information" size="x-large" class="large-font" </v-icon>
                        </v-row>
                        <v-row align="center" justify="center" no-gutters class="py-6">
                            <div class="text-subtitle-1 font-weight-light text-center">
                                No User found under this Project. Click the following button to Add new user.
                            </div>
                        </v-row>
                        <v-row align="center" justify="center" no-gutters>
                            <v-btn @click="userDialog = true" size="large" variant="outlined"
                                prepend-icon="mdi-account-plus">
                                Add User to Project
                            </v-btn>
                        </v-row>
                    </v-container>
                </v-sheet>
            </v-col>
        </v-row>
        <v-row justify="space-between">
            <v-col>
                <v-row justify="space-between">
                    <v-col cols="6">
                        <div class="d-flex align-center gap-2">
                            <v-btn v-if="extendProjectSoftware == false" icon="mdi-chevron-right" @click="extendProjectSoftware = true">
                            </v-btn>
                            <v-btn v-if="extendProjectSoftware == true" icon="mdi-chevron-down" @click="extendProjectSoftware = false">
                            </v-btn>
                            <h5 class="text-h5 py-4">Project Software</h5>
                        </div>
                    </v-col>
                    <v-col cols="4" class="d-flex justify-end align-center">
                        <v-btn 
                            block 
                            @click="softwareDialog = true" 
                            size="large" 
                            prepend-icon="mdi-gamepad-variant"
                            min-width="300"
                            v-if="userHasAdminAccess || can(project?.id,'manage_project_software')"
                            >
                            Add software to Project
                        </v-btn>
                    </v-col>
                </v-row>
                <v-table v-if="allowedSoftware.length > 0 && extendProjectSoftware == true">
                    <thead>
                        <tr>
                            <th></th>
                            <th class="text-left">
                                Software Identifier
                            </th>
                            <th class="text-center" v-if="userHasAdminAccess  || can(project?.id,'manage_project_software')">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="item in allowedSoftware" :key="item.software_uuid">
                            <td><v-icon>mdi-gamepad-variant</v-icon></td>
                            <td>{{ item.software_uuid }}</td>
                            <td class="text-center" v-if="userHasAdminAccess || can(project?.id,'manage_project_software')">
                                <v-btn @click="confirmSoftwareMappingDeletion(item.software_uuid)" density="default"
                                    icon="mdi-trash-can"></v-btn>
                            </td>
                        </tr>
                    </tbody>
                </v-table>
                <v-sheet rounded v-if="allowedSoftware.length == 0">
                    <v-container>
                        <v-row align="center" justify="center" no-gutters>
                            <v-icon icon="mdi-information" size="x-large" class="large-font" </v-icon>
                        </v-row>
                        <v-row align="center" justify="center" no-gutters class="py-6">
                            <div class="text-subtitle-1 font-weight-light text-center">
                                No DAG allowed for this Project. Click the following button to allow a DAG.
                            </div>
                        </v-row>
                        <v-row align="center" justify="center" no-gutters>
                            <v-btn @click="softwareDialog = true" size="large" variant="outlined"
                                prepend-icon="mdi-gamepad-variant">
                                Add DAG to project
                            </v-btn>
                        </v-row>
                    </v-container>
                </v-sheet>
            </v-col>
        </v-row>
        <v-row justify="space-between">
            <v-col>
                <v-row justify="space-between">
                    <v-col cols="6">
                        <div class="d-flex align-center gap-2">
                            <v-btn v-if="extendMultiinstallableExtensions == false" icon="mdi-chevron-right" @click="extendMultiinstallableExtensions = true">
                            </v-btn>
                            <v-btn v-if="extendMultiinstallableExtensions == true" icon="mdi-chevron-down" @click="extendMultiinstallableExtensions = false">
                            </v-btn>
                            <h5 class="text-h5 py-4">Multiinstallable Applications</h5>
                        </div>
                    </v-col>
                </v-row>
                <v-table v-if="extendMultiinstallableExtensions == true">
                    <thead>
                    <tr>
                        <th></th>
                        <th class="text-left">
                            Name
                        </th>
                        <th class="text-center" v-if="userHasAdminAccess  || can(project?.id,'manage_project_extensions')">
                            Launch
                        </th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr v-for="item in multiinstallableExtensions" :key="item.releaseName">
                        <td><v-icon>mdi-application-outline</v-icon></td>
                        <td>{{ item.annotations["ui-visible-name"] }}</td>
                        <td class="text-center" v-if="userHasAdminAccess || can(project?.id,'manage_project_extensions')">
                            <v-btn 
                            density="default"
                            @click="launchApplication(item)">
                                Launch
                            </v-btn>
                        </td>
                    </tr>
                    </tbody>
                </v-table>
            </v-col>
        </v-row>
        <v-row>
            <v-col>
                <v-row justify="space-between">
                    <v-col cols="6">
                        <div class="d-flex align-center gap-2">
                            <v-btn v-if="extendActiveApplications == false" icon="mdi-chevron-right" @click="extendActiveApplications = true">
                            </v-btn>
                            <v-btn v-if="extendActiveApplications == true" icon="mdi-chevron-down" @click="extendActiveApplications = false">
                            </v-btn>
                            <h5 class="text-h5 py-4">Active Project Applications</h5>
                        </div>
                    </v-col>
                </v-row>
                <v-table v-if="extendActiveApplications == true">
                    <thead>
                    <tr>
                        <th></th>
                        <th class="text-left">
                            Name
                        </th>
                        <th>Links</th>
                        <th class="text-center" v-if="userHasAdminAccess  || can(project?.id,'manage_project_extensions')">
                            Uninstall
                        </th>
                    </tr>
                    </thead>
                    <tbody>
                    <tr v-for="item in activeApplications" :key="item.releaseName">
                        <td><v-icon>mdi-application-outline</v-icon></td>
                        <td>{{ item.annotations["kaapana.ai/display-name"] }}</td>
                        <td>
                              <div class="flex gap-2 justify-center">
                                <a 
                                v-for="path in item.paths" 
                                :key="path"
                                :href="getFullEndpoint(path)"
                                target="_blank"
                                rel="noopener noreferrer"
                                >
                                <v-icon>mdi-open-in-new</v-icon>
                                </a>
                            </div>
                        </td>
                        <td class="text-center" v-if="userHasAdminAccess || can(project?.id,'manage_project_extensions')">
                            <v-btn 
                            density="default"
                            icon="mdi-trash-can"
                            @click="uninstallApplication(item)"
                            >
                            </v-btn>
                        </td>
                    </tr>
                </tbody>
                </v-table>
            </v-col>
        </v-row>

    </v-container>
    <v-dialog v-model="softwareDialog" max-width="1000">
        <AddSoftwareToProject :projectId="project?.id || ''" :projectName="project?.name || ''" :current-software="allowedSoftware"
            :oncancel="resetSoftwareFormValues" :onsuccess="handleSoftwareSubmit" />
    </v-dialog>
    <v-dialog v-model="userDialog" max-width="1000">
        <AddUserToProject :projectId="project?.id || ''" :projectName="project?.name || ''" :current-user-ids="userIds" :onsuccess="handleUserSubmit"
            :oncancel="resetUserFormValues" />
    </v-dialog>
    <v-dialog v-model="userEditDialog" max-width="1000">
        <AddUserToProject :projectId="project?.id || ''" :projectName="project?.name || ''" action-type="update" :selected-user="selectedUser"
            :current-role="selectedUser?.role" :onsuccess="handleUserSubmit" :oncancel="resetUserFormValues" />
    </v-dialog>
    <v-dialog v-model="launchApplicationDialog" max-width="1000">
        <LaunchApplication 
        :extension="selectedExtension"
        @submit="handleExtensionSubmit"
        @close="launchApplicationDialog = false"
        />
    </v-dialog>
    <confirm ref="confirm"></confirm>
</template>

<script lang="ts">
import { defineComponent } from 'vue'
import { aiiApiGet, aiiApiDelete, kubeHelmGet, kubeHelmPost } from '@/common/aiiApi.service'
import { ProjectItem, UserItem, UserRole, Software } from '@/common/types'
import AddUserToProject from '@/components/AddUserToProject.vue'
import store from "@/common/store";
import { usePermissions } from '@/permissions/usePermissions';
import LaunchApplication from '@/components/LaunchApplication.vue';


interface User extends UserItem {
    role?: UserRole
}

export default defineComponent({
    components: {
        AddUserToProject,
        LaunchApplication
    },
    props: {},
    setup () {
        const { can } = usePermissions();

        return {
            can
        };
    },
    data() {
        return {
            // @ts-ignore
            projectId: this.$route.params.id as string, // Access the route param
            project: null as ProjectItem | null,
            users: [] as User[],
            userDialog: false,
            userIds: [] as string[],
            fetchingUser: false,
            userEditDialog: false,
            selectedUser: undefined as User | undefined,
            userHasAdminAccess: false,
            allowedSoftware: [] as Software[],
            softwareDialog: false,
            multiinstallableExtensions: [] as any[],
            installedExtensions: [] as any[],
            activeApplications: [] as any[],
            launchApplicationDialog: false,
            selectedExtension: null as any,
            extendProjectSoftware: false,
            extendProjectUsers: false,
            extendMultiinstallableExtensions: false,
            extendActiveApplications: false,
        };
    },
    mounted() {
        this.fetchProject();
        this.fetchProjectUsers();
        this.fetchProjectSoftware();
        this.fetchMultiinstallableApplications();
        this.fetchActiveApplications();

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
        '$route.params.id': function (newprojectId: string) {
            this.projectId = newprojectId;
        },
        'users': function (newUsers: User[]) {
            let tempUserIds: string[] = []
            newUsers.forEach((user, index) => {
                this.fetchProjectUserRole(user.id, index);
                tempUserIds.push(user.id);
            });
            this.userIds = [...tempUserIds];
        },
        'project': function() {
            this.fetchActiveApplications()
        },
    },
    methods: {
        getFullEndpoint(path: string) {
         return `${window.location.origin}${path}`;
        },
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
        async fetchMultiinstallableApplications() {
            // Get all installable applications
            try {
                const extensions = await kubeHelmGet(`extensions`)
                
                const multiinstallableExtensions = extensions.filter((item:any) => {
                    return item.multiinstallable === "yes"});
                this.multiinstallableExtensions = multiinstallableExtensions.filter((item:any) => {
                        return item.installed === "no";});
                this.installedExtensions = multiinstallableExtensions.filter((item:any) => {
                        return item.installed === "yes";});
            } catch (error: unknown) {
                console.log(error);
            }
        },
        async launchApplication(item :any) {
            this.selectedExtension = item;
            this.launchApplicationDialog = true;
        },
        async handleExtensionSubmit({ extension, values }: { extension: any; values: any }) {
            console.log("Submitting:", extension, values);
            // send to API here
            const data = {
                name: extension.name,
                version: extension.version,
                keywords: extension.keywords,
                extension_params: values,
            }
            try {
                await kubeHelmPost(`helm-install-chart`, data)
            } catch (error: unknown) {
                console.log(error);
            }
            
            this.launchApplicationDialog = false;
        },
        async uninstallApplication(item: any) {
            const data = {
                release_name: item.release_name,
            }
            try {
                kubeHelmPost('helm-delete-chart', data)
                this.fetchActiveApplications();
            } catch (error: unknown) {
                console.log(error);
            }
        },
        async fetchActiveApplications() {
            // Get all installable applications
            if (this.project) {
                const projectName = this.project.name
                try {
                    const applications = await kubeHelmGet(`active-applications`)

                    this.activeApplications = applications.filter((item: any) => {return item.project === projectName});
                    console.log(JSON.stringify(this.activeApplications))
                } catch (error: unknown) {
                    console.log(error);
                }
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
        fetchProject() {
            if (this.projectId) {
                try {
                    aiiApiGet(`projects/${this.projectId}`).then((project: ProjectItem) => {
                        this.project = project;
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
        fetchProjectSoftware() {
            if (this.projectId) {
                try {
                    aiiApiGet(`projects/${this.projectId}/software-mappings`).then((software: any) => {
                        console.log(software)
                        this.allowedSoftware = software.sort((a: Software, b: Software) => {
                            return a.software_uuid.localeCompare(b.software_uuid);
                        });
                    })
                } catch (error: unknown) {
                    console.log(error);
                }
            }
        },
        deleteSoftwareMapping(softwareUuid: string) {
            const data = [
                {
                    software_uuid: softwareUuid,
                },
            ];
            if (this.projectId) {
                try {
                    aiiApiDelete(`projects/${this.projectId}/software-mappings`, {}, data).then((success: boolean) => {
                        if (success) {
                            this.fetchProjectSoftware();
                        }
                    })
                } catch (error: unknown) {
                    console.log(error);
                }
            }
        },
        async confirmSoftwareMappingDeletion(softwareUuid: string) {
            // @ts-ignore
            if (await this.$refs.confirm.open('Delete Software from project', 'Are you sure?', { color: 'red' })) {
                this.deleteSoftwareMapping(softwareUuid);
            }
        },
        resetSoftwareFormValues() {
            this.softwareDialog = false;
        },
        handleSoftwareSubmit(success: boolean = true) {
            if (success) {
                this.fetchProjectSoftware();
            }
            this.resetSoftwareFormValues();
        },
    }
})
</script>

<style scoped>
.large-font {
    font-size: 40px;
}
</style>