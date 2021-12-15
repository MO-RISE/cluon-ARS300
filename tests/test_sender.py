import time
import json
from datetime import datetime

from pycluon import OD4Session

from main import cluon_send, memo


def test_sender():
    called = False
    received_envelope = None

    session = OD4Session(111)

    def callback(envelope):
        nonlocal called, received_envelope
        called = True
        received_envelope = envelope

    session.add_data_trigger(10000, callback)

    msg = memo.memo_raw_Raw()
    msg.data = json.dumps({"test": "value"})

    cluon_send([(10000, datetime.fromtimestamp(3), msg)])

    time.sleep(0.01)

    assert called
    received_message = memo.memo_raw_Raw()
    received_message.ParseFromString(received_envelope.serialized_data)
    assert received_envelope.sampled_at == datetime.fromtimestamp(3)
    assert json.loads(received_message.data) == {"test": "value"}
