'''
Gunicorn config
'''

import multiprocessing

bind = "10.53.145.255:8000"

workers = multiprocessing.cpu_count() * 2 + 1

daemon = True

accesslog = './gunicorn_acess.log'

errorlog = './gunicorn_error.log'

loglevel = 'info'


'''
gunicorn -c conf.py lantern.wsgi

pstree -ap | grep gunicorn

kill -HUP 1234

kill -9 1234
'''