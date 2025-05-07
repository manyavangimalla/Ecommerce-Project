import requests
import os

def send_notification(user_id, notification_type, data):
    try:
        response = requests.post(
            f"{os.environ.get('API_URL', 'http://localhost:5000')}/api/notifications",
            json={
                'user_id': user_id,
                'type': notification_type,
                'data': data
            }
        )
        return response.status_code == 201
    except:
        return False 