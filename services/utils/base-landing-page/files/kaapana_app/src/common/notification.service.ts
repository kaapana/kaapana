import ResultsBrowser from "@/views/ResultsBrowser.vue";
import httpClient from "./httpClient";
const KAAPANA_NOTIFICATION_ENDPOINT = process.env.VUE_APP_NOTIFICATIONS_API_ENDPOINT!;

export type NotificationID = string;

export interface Notification {
    topic: string,
    title: string,
    description: string,
    icon: string,
    link: string,
    id: string,
    timestamp: Date,
}

enum NotificationEventType {
  NEW = "new",
  READ = "read",
}

export interface NotificationEvent {
  id: string,
  type: NotificationEventType
}

export const fetch_notifications = async (): Promise<Notification[]> => {
    const response = await httpClient.get(`${KAAPANA_NOTIFICATION_ENDPOINT}/v1`);
    return response.data;
}

export const read_notification = async (id : NotificationID) => {
    return await httpClient.put(`${KAAPANA_NOTIFICATION_ENDPOINT}/v1/${id}/read`);
}

export class NotificationWebsocket {
    private connection: WebSocket;

    constructor(notifcations_endpoint: string = KAAPANA_NOTIFICATION_ENDPOINT) {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsHost = window.location.host;
        const wsPath = `${notifcations_endpoint}/ws`;

        console.log("Notifications connecting to WebSocket")
        this.connection = new WebSocket(`${wsProtocol}//${wsHost}${wsPath}`);

        this.connection.onopen = function (event: Event) {
          console.log(event);
          console.log("Notifications WebSocket connection established.");
        }
    }

    public onMessage(handler: (event: NotificationEvent) => void): void {
      this.connection.addEventListener('message',
        (e: MessageEvent) => {
          const parsed = JSON.parse(e.data);
          handler(parsed);
        }
      );
    }

    public onOpen(handler: (ev: Event) => void): void {
      this.connection.addEventListener('open', handler);
    }

    public onClose(handler: (ev: CloseEvent) => void): void {
      this.connection.addEventListener('close', handler);
    }

    public onError(handler: (ev: Event) => void): void {
      this.connection.addEventListener('error', handler);
    }
}