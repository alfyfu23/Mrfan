from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def notify_conversation_event(user_ids, event_name, conversation_id):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    safe_ids = {uid for uid in user_ids if uid}
    if not safe_ids:
        return
    payload = {
        'type': 'conversation_event',
        'event': event_name,
        'conversation': conversation_id,
    }
    for uid in safe_ids:
        async_to_sync(channel_layer.group_send)(f'user_{uid}', payload)
