#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os


class Config_Dev(object):
    SQLALCHEMY_DATABASE_URI = 
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    # 要比数据库 wait_timeout 参数要小
    SQLALCHEMY_POOL_RECYCLE = 50
    SQLALCHEMY_ECHO = False
    ID_TOKEN_DEFAULT_EXPIRES = 8640000

    ACCESS_TOKEN_DEFAULT_EXPIRES = 86400
    CORS_ORIGINS = []

    APP_ID = ""
    APP_SECRET = ""

    AUTH_SERVER_HOST = 
    AUTH_SERVER_LOGIN_URL = 
    AUTH_SERVER_LOGOUT_URL = 
    Powers = {}
    KVMHOSTS = {
        'DEV':['192.168.'],
        'TEST': ['192.168.']
    }
    CODEHUB_TOKEN = ""
    BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),'app/playbooks')
class Config_Ga(Config_Dev):
    SQLALCHEMY_DATABASE_URI = ""
    SQLALCHEMY_ECHO = False
    AUTH_SERVER_HOST = 
    AUTH_SERVER_LOGIN_URL = 
    AUTH_SERVER_LOGOUT_URL = 

    APP_ID = ""
    APP_SECRET = ""


Config = Config_Dev

if os.environ.get('ENV_CODE') == "GA":
    Config = Config_Ga
