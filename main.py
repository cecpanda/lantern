# -*- coding: utf-8 -*-

import json
import requests

url = 'http://127.0.0.1:8000/tft/update/180709-102955-821697/'

headers = {
    #'Content-Type': 'application/json',
    'Authorization': 'JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoyLCJ1c2VybmFtZSI6IjAzMTUyIiwiZXhwIjoxNTMxNzA1NDE5LCJlbWFpbCI6IiIsIm9yaWdfaWF0IjoxNTMxMTAwNjE5fQ.Mv3lYeCCCTeMd3SIZ_rIgt_vaEA7gQZGfzolw9GrSYw'
}

data = {
    'draft': False,
    'eq': ['cak-01k', 'CAK-02K'],
    'kind': '185',
    'step': '03100,18700',
    'found_time': '2018-07-07T20:12:25.347335+08:00',
    'found_step': 'array',
    'reason': 'woca',
    'users': ['0', '1'],
    'charge_users': ['2', '03152'],
    'desc': 'woca',
    'start_time': '2018-07-07T20:12:25.347335+08:00',
    'end_time': '2018-07-07T20:15:25.347335+08:00',
    'lot_num': 10,
    'lots': ['PAD1K1', 'PAD1K2'],
    'condition': 'woca',
    'deal': 'wo',
    'remark': 'woca',
}


files = (
    ('reports', open('./static/panda.jpg', 'rb')),
    ('reports', open('./static/pyt.jpg', 'rb'))
)


res = requests.post(url, data=data, files=files, headers=headers)

print(res.json())
