export type ProjectItem = {
    id: string,
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
    groups?: string[],
    realm_roles?: string[],
}

export type UserRole = {
    id: number,
    description: string,
    name: string,
}

export type Software = {
    software_uuid: string
}