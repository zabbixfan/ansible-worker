#!/usr/bin/env python
# -*- coding: utf-8 -*-
from . import api
from flask import g,request
from flask_restful import Resource, reqparse
from ..common.ApiResponse import ApiResponse,ResposeStatus
from ..common.AuthenticateDecorator import need_sign
from app.domains.ansibles import *
from app.common.RequestInputs import kvmActionType,json_dict
def pb_args():
    rp = reqparse.RequestParser()
    rp.add_argument('params',type=dict)
    rp.add_argument('playBookName')
    rp.add_argument('callBack',default='')
    rp.add_argument('ips',action='append')
    return rp.parse_args()

def adHoc_args():
    rp = reqparse.RequestParser()
    rp.add_argument('params')
    rp.add_argument('callBack')
    rp.add_argument('modulename')
    rp.add_argument('ips',action='append',default=[])
    return rp.parse_args()


class AnsiblePb(Resource):
    @need_sign()
    def post(self):
        args=pb_args()
        res,status=ansibleWoker(playBookName=args.playBookName,
                                ips=args.ips,
                                params=args.params,
                                callBack=args.callBack)
        return ApiResponse(res,status)
class AnsibleHoc(Resource):
    #@need_sign()
    def post(self):
        args=adHoc_args()
        res,status = ansibleAdHoc(moduleName=args.modulename,params=args.params,ips=args.ips)
        return ApiResponse(res,status)
        pass

api.add_resource(AnsiblePb,'/ansiblepb')
api.add_resource(AnsibleHoc,'/ansiblead')