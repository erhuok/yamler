#encoding:utf8
from queue import Queue
import json
#from pyapns import configure, provision, notify
import sys 
reload(sys) 
sys.setdefaultencoding('utf8') 
import os
from APNSWrapper import *
import binascii

if not sys.argv[1:]:
    print "Usage python pagedata.py [OPTIONS] query words\n"
    print "Options are:"
    print "-t, --type \t 请输入类型，如iphone"
    sys.exit(0)

#参数解析
i = 1
while (i<len(sys.argv)):
    arg = sys.argv[i]
    if arg == '-t' or arg == '--type':
        i +=1
        type = sys.argv[i]
    i += 1

def send_iphone_notify():
    try:
        queue = Queue('notify')
        #configure({'HOST': 'http://localhost:7077/'})
        #provision('justoa', open(os.path.join(os.path.dirname(__file__), 'iphone/cert.pem')).read(), 'production')
        while 1:
            data = queue.rpop()
            if data:
                wrapper = APNSNotificationWrapper(os.path.join(os.path.dirname(__file__), 'iphone/cert.pem'), True)
                message = APNSNotification()
                data = json.loads(data)
                deviceToken = binascii.unhexlify(data['iphone_token'])
                message.token(deviceToken)
                alert = APNSAlert()
                body = str(data['message']) 
                alert.body(body)
                message.alert(alert)
                message.badge(5)
                message.sound()
                wrapper.append(message)
                wrapper.notify()
                #notify('justoa', data['iphone_token'], {'aps':{'alert': data['message'], 'sound': 'default'}})
    except:
        pass

if type == 'iphone':
    send_iphone_notify()
