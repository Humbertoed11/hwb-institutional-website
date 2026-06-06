import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from main_app import app

def test_api():
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'humberto'
        sess['role'] = 'Admin'
    
    # Test getting all beacons
    response = client.get('/api/v1/beacons')
    print("ALL BEACONS STATUS:", response.status_code)
    data = response.get_json()
    print("ALL BEACONS COUNT:", len(data['data']))
    for b in data['data']:
        print(f" - {b['name']} ({b['tier']}): Lat {b['latitude']}, Lng {b['longitude']}, Score {b['score']}, Count {b['count']}")
        
    # Test filtering by sky tier
    response_sky = client.get('/api/v1/beacons?tier=sky')
    print("SKY BEACONS STATUS:", response_sky.status_code)
    data_sky = response_sky.get_json()
    print("SKY BEACONS COUNT:", len(data_sky['data']))
    for b in data_sky['data']:
        print(f" - {b['name']} ({b['tier']})")
        assert b['tier'] == 'sky'

    # Test filtering by clouds tier
    response_clouds = client.get('/api/v1/beacons?tier=clouds')
    print("CLOUDS BEACONS STATUS:", response_clouds.status_code)
    data_clouds = response_clouds.get_json()
    print("CLOUDS BEACONS COUNT:", len(data_clouds['data']))
    for b in data_clouds['data']:
        print(f" - {b['name']} ({b['tier']})")
        assert b['tier'] == 'clouds'

    print("ALL TESTS PASSED SUCCESSFULLY.")

if __name__ == '__main__':
    test_api()
