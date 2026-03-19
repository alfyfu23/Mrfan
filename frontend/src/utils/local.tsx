
export const _store = (name: string, value: string) => {
    localStorage.setItem(name, value);
}

export const _read = (name: string) => {
    return localStorage.getItem(name);
}