#!/usr/bin/env python
# -*- coding: utf-8 -*-


def kvmActionType(value):
    if value not in ['createVm','startVm','stopVm','deleteVm','restartVm']:
        raise ValueError("kvm action must in createVm,startVm,stopVm,deleteVm,restartVm")
    return value
def _get_integer(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError('{0} is not a valid integer'.format(value))


class json_dict(object):
    __name__ = "json_dict"

    def __init__(self, keys=[]):
        self.keys = keys

    def __call__(self, value):
        for key in self.keys:
            if not value.has_key(key):
                raise ValueError("required parameter missing '%s'" % key)
        return value




