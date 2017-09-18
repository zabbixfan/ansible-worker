#!/usr/bin/env python
# -*- coding: utf-8 -*-
from . import api
from flask import g
from flask_restful import Resource, reqparse
from ..common.ApiResponse import ApiResponse
from ..common.AuthenticateDecorator import need_user


def get_args(return_parse_args=True):
    rp = reqparse.RequestParser()
    rp.add_argument("name", type=unicode, required=True, nullable=False)
    return rp.parse_args() if return_parse_args else rp


class Demo(Resource):
    @need_user()
    def get(self):
        args = get_args()
        return ApiResponse({
            "say": "Hello " + args.name,
            "from": g.user.get("name")
        })


api.add_resource(Demo, "/")
