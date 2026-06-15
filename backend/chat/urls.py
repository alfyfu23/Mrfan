# chat/urls.py
from django.urls import path

from .views import (
    announce,
    create_friend_conversation,
    create_group,
    delete_message,
    disband_group,
    edit_message,
    exit_group,
    get_announcements,
    get_pinned_conversations,
    get_user_invitations,
    group_info,
    history,
    home,
    # 群成员邀请功能
    invite_to_group,
    list_group_invitations,
    mark_read,
    # 置顶功能
    pin_conversation,
    recall_message,
    remove_member,
    review_group_invitation,
    # new
    set_group_nickname,
    set_member_role,
    set_mute_pin,
    transfer_owner,
    unpin_conversation,
    update_group_info,
    upload,
)

urlpatterns = [
    path('history', history, name='history'),
    path('create/friend', create_friend_conversation, name="create_friend_conversation"),
    path('home', home, name='home'),
    # group
    path('group/create', create_group, name='create_group'),
    path('group/update', update_group_info, name='update_group_info'),
    path('group/info', group_info, name='group_info'),
    path('group/nickname', set_group_nickname, name='set_group_nickname'),
    path('group/role', set_member_role, name='set_member_role'),
    path('group/transfer', transfer_owner, name='transfer_owner'),
    path('group/announce', announce, name='announce'),
    path('group/announcements', get_announcements, name='get_announcements'),
    path('group/remove', remove_member, name='remove_member'),
    path('group/exit', exit_group, name='exit_group'),
    path('group/disband', disband_group, name='disband_group'),
    # message
    path('message/read', mark_read, name='mark_read'),
    path('message/edit', edit_message, name='edit_message'),
    path('message/recall', recall_message, name='recall_message'),
    path('message/delete', delete_message, name='delete_message'),
    # member settings
    path('member/set', set_mute_pin, name='set_mute_pin'),
    # upload
    path('upload', upload, name='upload'),
    # 置顶功能
    path('pin', pin_conversation, name='pin_conversation'),
    path('unpin', unpin_conversation, name='unpin_conversation'),
    path('pinned', get_pinned_conversations, name='get_pinned_conversations'),
    # 群成员邀请功能
    path('group/invite', invite_to_group, name='invite_to_group'),
    path('group/invitations', list_group_invitations, name='list_group_invitations'),
    path('group/invitation/review', review_group_invitation, name='review_group_invitation'),
    path('user/invitations', get_user_invitations, name='get_user_invitations'),
]
