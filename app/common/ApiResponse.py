#!/usr/bin/env python
# -*- coding: utf-8 -*-
class ApiResult(object):
    def __init__(self, code, message, status):
        self.status_code = code
        self.message = message
        self.restful_status = status


class ResposeStatus(object):
    Success = ApiResult('success', '成功', 200)
    Fail = ApiResult("fail", "失败", 400)
    AuthenticationFailed = ApiResult("verify fail", "身份失效", 401)
    Powerless = ApiResult("power less", "没有权限执行该操作", 403)
    SignFail = ApiResult("verify fail", "身份失效", 401)







def ApiResponse(obj=None, status=ResposeStatus.Success):
    return {
               "status": status.status_code,
               "message": status.message,
               "data": obj
           }, status.restful_status
