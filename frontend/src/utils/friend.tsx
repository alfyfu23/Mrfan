import { User } from '@/types/User';
import { BACKEND_URL } from '@/constant/strings';

export function get_frineds_api(token: string) {
    /**
     * 获得某个用户的好友列表
     * 
     * 参数：
     * 1. 此用户token
     * 
     * 返回：
     * [friends, pendings]
     */
    let friend_ids: number[] = [];
    let pending_ids: number[] = [];
    return fetch(`https://${BACKEND_URL}/friend/list`, {
        method: "GET",
        headers: {
            "Accept": "application/json",
            "Authorization": "Bearer " + token
        }
    }).then(response => {
        return response.json();
    }).then(data => {
        console.log(data);
        friend_ids = data['friends'];
        pending_ids = data['pending'];
        console.log(`get ${friend_ids.length} friends`);
        return [friend_ids, pending_ids];
    }).catch(err => {
        console.error("请求出错:", err)
        return [[], []];
    });
}

export async function get_friend_info(token: string, id: number): Promise<User> {
    const response = await fetch(`https://${BACKEND_URL}/account/get_info?target=${id}`, {
        method: "GET",
        headers: {
            "Accept": "application/json",
            "Authorization": "Bearer " + token
        }
    });
    const data = await response.json();
    const user: User = {
        id: id,
        name: data['username'],
        avatar: data['avatar'],
        info: data['info'],
        is_active: data['is_active']
    };
    return user;
}

export async function checkFriendship(token: string, userId: number): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/friend/check/${userId}`, {
            method: "GET",
            headers: {
                "Accept": "application/json",
                "Authorization": "Bearer " + token
            }
        });
        const data = await response.json();
        return data.code === 0; // 如果返回成功，表示是好友
    } catch (err) {
        console.error("检查好友状态出错:", err);
        return false;
    }
}

export async function sendFriendRequest(token: string, userId: number): Promise<boolean> {
    try {
        const response = await fetch(`https://${BACKEND_URL}/friend/add/${userId}`, {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Authorization": "Bearer " + token
            }
        });
        const data = await response.json();
        return data.code === 0; // 如果返回成功，表示好友申请已发送
    } catch (err) {
        console.error("发送好友申请出错:", err);
        return false;
    }
}