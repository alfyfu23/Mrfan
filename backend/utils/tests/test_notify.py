from unittest.mock import MagicMock, patch


@patch('utils.notify.get_channel_layer')
def test_notify_no_channel_layer(mock_get_channel_layer):
    mock_get_channel_layer.return_value = None
    from utils.notify import notify_conversation_event
    notify_conversation_event([1, 2], 'test_event', 123)
    mock_get_channel_layer.assert_called_once()


@patch('utils.notify.get_channel_layer')
@patch('utils.notify.async_to_sync')
def test_notify_empty_ids(mock_async, mock_get_channel_layer):
    mock_get_channel_layer.return_value = MagicMock()
    from utils.notify import notify_conversation_event
    notify_conversation_event([], 'test_event', 123)
    mock_async.assert_not_called()


@patch('utils.notify.get_channel_layer')
@patch('utils.notify.async_to_sync')
def test_notify_filters_falsy_ids(mock_async, mock_get_channel_layer):
    mock_get_channel_layer.return_value = MagicMock()
    from utils.notify import notify_conversation_event
    notify_conversation_event([1, None, 0, 2], 'test_event', 123)
    assert mock_async.call_count == 2


@patch('utils.notify.get_channel_layer')
@patch('utils.notify.async_to_sync')
def test_notify_sends_correct_payload(mock_async, mock_get_channel_layer):
    mock_get_channel_layer.return_value = MagicMock()
    from utils.notify import notify_conversation_event
    notify_conversation_event([42], 'group_disbanded', 99)
    mock_async.assert_called_once()
    send_call = mock_async.return_value
    sent_args = send_call.call_args[0]
    assert sent_args[0] == 'user_42'
    sent_payload = sent_args[1]
    assert sent_payload['type'] == 'conversation_event'
    assert sent_payload['event'] == 'group_disbanded'
    assert sent_payload['conversation'] == 99
