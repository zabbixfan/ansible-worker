from app.common.api_sign_sdk import post_with_sign
url = "http://192.168.6.120:8888/api/ansiblepb"
body = {
    "playBookName": "useradd",
    "params": {
        "login_name": 'songcheng3215',
        "rule": 'admin'
    },
    "ips": ['192.168.4.119','192.168.4.120']
    # "callBack": "http://192.168.6.120:6210/api/webhook/999"
}
response = post_with_sign(url=url, json=body).json()
import json
print json.dumps(response,indent=4)