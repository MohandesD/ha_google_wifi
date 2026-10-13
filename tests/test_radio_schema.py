"""Radio evidence must not export credentials or identity values."""
import json
from gwi_test.radio_schema import radio_schema

def test_radio_evidence_is_bounded_and_contains_no_private_values():
    payload={'mesh':{'signal':-67,'quality':'GOOD','ssid':'private-network','password':'private-password','token':'private-token','deviceName':'private-device'},'stations':[{'rssi':-72,'macAddress':'aa:bb:cc:dd:ee:ff','ipAddress':'192.168.50.10','signalQuality':'GREAT'}]}
    result=radio_schema(payload)
    text=json.dumps(result)
    for private in ('private-network','private-password','private-token','private-device','aa:bb:cc:dd:ee:ff','192.168.50.10'):
        assert private not in text
    assert result['radio_samples']['mesh.signal']==[-67]
    assert result['radio_samples']['stations[].rssi']==[-72]
    assert radio_schema({'signal':True,'rssi':float('nan'),'noise':float('inf')})['radio_samples']=={}
