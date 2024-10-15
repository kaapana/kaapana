export type ProjectItem = {
    id: number,
    external_id?: number,
    name: string,
    description?: string,
}

export type UserItem = {
    id: string,
    username: string,
    first_name: string,
    last_name: string,
    email_verified: boolean,
}

export type UserRole = {
    id: number,
    description: string,
    name: string,
}