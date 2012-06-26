from pyapns import configure, provision, notify
configure({'HOST': 'http://localhost:7077/'})
provision('justoa', open('cert.pem').read(), 'production')
s = '94d9f9607fbd0889b550430619912b1d1276749488be7c5f26e6c37b750a8bcc'
notify('justoa', s, {'aps':{'alert': 'Hello!'}})
