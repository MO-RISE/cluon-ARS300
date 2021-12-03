import time
from pycluon import OD4Session
from pycluon.importer import import_odvd

from main import cluon_send, opendlv


def test_sender():
    called = False
    received_envelope = None

    session = OD4Session(111)

    def callback(envelope):
        nonlocal called, received_envelope
        called = True
        received_envelope = envelope

    session.add_data_trigger(1134, callback)

    msg = opendlv.opendlv_logic_perception_ObjectDistance()
    msg.objectId = 42
    msg.distance = 78.5

    cluon_send([(1134, 3, msg)])

    time.sleep(0.01)

    assert called
    received_message = opendlv.opendlv_logic_perception_ObjectDistance()
    received_message.ParseFromString(received_envelope.serialized_data)
    assert received_envelope.sampled == 3
    assert received_message.objectId == 42
    assert received_message.distance == 78.5
