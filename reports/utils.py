# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, CloudBlue
# All rights reserved.
#

from datetime import datetime


def convert_to_datetime(param_value):
    if param_value == "" or param_value == "-":
        return "-"

    return datetime.strptime(
        param_value.replace("T", " ").replace("+00:00", ""),
        "%Y-%m-%d %H:%M:%S",
    )


def get_basic_value(base, value):
    if base and value in base:
        return base[value]
    return '-'


def get_value(base, prop, value):
    if prop in base:
        return get_basic_value(base[prop], value)
    return '-'


def parameter_value(parameter_id, parameter_list, default="-"):
    try:
        parameter = list(filter(lambda param: param['id'] == parameter_id, parameter_list))[0]
        return parameter['value']
    except IndexError:
        return default
