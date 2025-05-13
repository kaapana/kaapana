<template>
    <div>
        <v-btn block depressed color="primary" class="blue darken-1" @click="dialog = true" title="Notifications">
            <v-icon>{{ notifications.length > 0 ? 'mdi-bell-ring' : 'mdi-bell-outline' }}</v-icon>
            <span class="ml-1">{{ notifications.length }}</span>
        </v-btn>

        <template>
            <v-dialog v-model="dialog" max-width="800">
                <v-card>
                    <v-card-title class="headline">
                        <v-icon>mdi-bell</v-icon>
                        <h3 class="ml-2">Notifications</h3>
                        <v-spacer />
                        <v-btn color="primary" @click="markAllAsRead">
                            <v-icon>mdi-check</v-icon>
                            Mark all as read
                        </v-btn>
                    </v-card-title>

                    <!-- only this wrapper scrolls -->
                    <v-card-text class="pa-0">
                        <div style="max-height: 1000px; overflow-y: auto;">
                            <v-expansion-panels multiple :value="defaultActivePanels">
                                <v-expansion-panel v-for="(items, topic) in groupedNotifications" :key="topic">
                                    <v-expansion-panel-header>
                                        <h3>{{ topic }}</h3>
                                    </v-expansion-panel-header>

                                    <v-expansion-panel-content>
                                        <v-list two-line>
                                            <v-list-item v-for="notif in items" :key="notif.id">
                                                <v-list-item-avatar>
                                                    <v-icon>{{ notif.icon || 'mdi-information' }}</v-icon>
                                                </v-list-item-avatar>

                                                <v-list-item-content>
                                                    <v-list-item-title>{{ notif.title }}</v-list-item-title>
                                                    <v-list-item-subtitle>
                                                        {{ new Date(notif.timestamp).toLocaleString() }}
                                                    </v-list-item-subtitle>
                                                    <div v-html="notif.description" class="mt-1"></div>
                                                </v-list-item-content>

                                                <v-list-item-action class="d-flex flex-row align-center"
                                                    style="gap: 8px;">
                                                    <v-btn color="primary" icon small v-if="notif.link"
                                                        :href="notif.link" target="_blank">
                                                        <v-icon>mdi-open-in-new</v-icon>
                                                    </v-btn>
                                                    <v-btn color="primary" text small
                                                        @click="readNotification(notif.id)">
                                                        <v-icon>mdi-check-circle-outline</v-icon>
                                                    </v-btn>
                                                </v-list-item-action>
                                            </v-list-item>
                                        </v-list>
                                    </v-expansion-panel-content>
                                </v-expansion-panel>
                            </v-expansion-panels>
                        </div>

                        <div v-if="notifications.length === 0" class="text-center grey--text pa-4">
                            No notifications
                        </div>
                    </v-card-text>

                    <v-card-actions>
                        <v-spacer />
                        <v-btn elevation="2" text @click="dialog = false">
                            Close
                        </v-btn>
                    </v-card-actions>
                </v-card>
            </v-dialog>
        </template>


    </div>
</template>
<script lang="ts">
import Vue from 'vue'
import { NotificationWebsocket, fetch_notifications, read_notification, Notification, NotificationEvent } from "@/common/notification.service"

export default Vue.extend({
    name: "NotificationButton",
    data() {
        return {
            notificationws: null as NotificationWebsocket | null,
            notifications: [] as Notification[],
            dialog: false
        };
    },
    methods: {
        updateNotifications() {
            fetch_notifications().then((n) => {
                this.notifications = n ?? [];
            });
        },
        readNotification(id: string) {
            read_notification(id).then(() => this.updateNotifications());
        },
        markAllAsRead() {
            if (!this.notifications.length) return;
            Promise.all(
                this.notifications.map(n => this.readNotification(n.id))
            );
        },
    },
    computed: {
        groupedNotifications(): Record<string, Notification[]> {
            return this.notifications.reduce((groups, notif) => {
                const key = notif.topic || 'Other'
                if (!groups[key]) groups[key] = []
                groups[key].push(notif)
                return groups
            }, {} as Record<string, Notification[]>)
        },
        defaultActivePanels(): number[] {
            return Object.keys(this.groupedNotifications).map((_, i) => i)
        },
    },
    mounted() {
        this.notificationws = new NotificationWebsocket()
        this.notificationws.onMessage((data: NotificationEvent) => {
            console.log(data);
            this.updateNotifications();
        });
        this.updateNotifications();
    }
});
</script>