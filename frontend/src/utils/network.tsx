export class InternalError extends Error {
    code: number;
    message: string;

    constructor(
        _type: number,
        _message: string,
    ) {
        super(_message);

        this.code = _type;
        this.message = _message;
    }

    toString(): string { return this.message; }
    valueOf(): string { return this.message; }
}

export interface ApiResponse {
    code: number;
    info?: string;
    [key: string]: unknown;
}

export function check_for_error(data: ApiResponse) {
    if (typeof data.code !== "number") {
        throw new InternalError(-1, "无效的响应格式");
    }
    if (data.code !== 0) {
        throw new InternalError(data.code, data.info ?? "未知错误");
    }
}


export enum NetworkErrorType {
    UNAUTHORIZED,
    REJECTED,
    CORRUPTED_RESPONSE,
    UNKNOWN_ERROR,
}

export class NetworkError extends Error {
    type: NetworkErrorType;
    message: string;

    constructor(
        _type: NetworkErrorType,
        _message: string,
    ) {
        super(_message);

        this.type = _type;
        this.message = _message;
    }

    toString(): string { return this.message; }
    valueOf(): string { return this.message; }
}

export const request = async (
    url: string,
    method: "GET" | "POST" | "PUT" | "DELETE",
    token?: string,
    body?: object,
) => {
    const headers: Record<string, string> = {};
    if (token) {
        headers.Authorization = token;
    }

    const response = await fetch(url, {
        method,
        body: body && JSON.stringify(body),
        headers
    });

    const data = await response.json();
    const code = Number(data.code);

    // HTTP status 401
    if (response.status === 401 && code === 2) {
        throw new NetworkError(
            NetworkErrorType.UNAUTHORIZED,
            "[401] " + data.info,
        );
    }
    else if (response.status === 401) {
        throw new NetworkError(
            NetworkErrorType.CORRUPTED_RESPONSE,
            "[401] " + data.info,
        );
    }

    // HTTP status 403
    if (response.status === 403 && code === 3) {
        throw new NetworkError(
            NetworkErrorType.REJECTED,
            "[403] " + data.info,
        );
    }
    else if (response.status === 403) {
        throw new NetworkError(
            NetworkErrorType.CORRUPTED_RESPONSE,
            "[403] " + data.info,
        );
    }

    // HTTP status 200
    if (response.status === 200 && code === 0) {
        return { ...data, code: undefined };
    }
    else if (response.status === 200) {
        throw new NetworkError(
            NetworkErrorType.CORRUPTED_RESPONSE,
            "[200] " + data.info,
        );
    }

    /**
     * TODO: 更精细的错误处理逻辑
     */
    throw new NetworkError(
        NetworkErrorType.UNKNOWN_ERROR,
        `[${response.status}] ` + data.info,
    );
};
