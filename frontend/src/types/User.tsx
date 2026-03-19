export interface Member {
    id: number,
    nickname: string,
    avatar?: string,
    is_active?: boolean,
    is_online?: boolean,
    display_username?: string,
};

export interface User {
    id: number,
    name: string,
    info?: string,
    avatar?: string,
    is_active?: boolean,
    is_online?: boolean,
}