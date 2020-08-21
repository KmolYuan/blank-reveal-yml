# -*- coding: utf-8 -*-

__author__ = "Yuan Chang"
__copyright__ = "Copyright (C) 2019-2020"
__license__ = "MIT"
__email__ = "pyslvs@gmail.com"

from os.path import isfile, join
from flask import Flask, request


def shutdown():
    """Manually close the server."""
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError("wrong server")
    func()
    return "Server shutting down..."


def serve(pwd: str, app: Flask, ip: str, port: int = 0) -> None:
    """Serve the app."""
    app.route('/exit', methods=['GET'])(shutdown)
    key = (join(pwd, 'localhost.crt'), join(pwd, 'localhost.key'))
    if isfile(key[0]) and isfile(key[1]):
        from ssl import SSLContext, PROTOCOL_TLSv1_2
        context = SSLContext(PROTOCOL_TLSv1_2)
        context.load_cert_chain(key[0], key[1])
        app.run(ip, port, ssl_context=context)
    else:
        app.run(ip, port)
