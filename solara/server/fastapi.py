import asyncio
import contextlib
import json
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Optional
from uuid import uuid4

import IPython.display
import ipywidgets as widgets
import react_ipywidgets
import websockets.exceptions
from fastapi import APIRouter, FastAPI, Request, Response, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse

from ..kitchensink import *
from . import app as appmod
from . import patch, server
from .kernel import BytesWrap, Kernel, WebsocketStreamWrapper

directory = Path(__file__).parent


# if asyncio.get_event_loop():
#     asyncio.create_task(solara_app.watch_app())


router = APIRouter()


# _kernel_spec = {
#     "display_name": "widgett-kernel",
#     "language": "python",
#     "argv": ["python", "doesnotworkthisway"],
#     "env": {},
#     "language": "python",
#     "interrupt_mode": "signal",
#     "metadata": {},
# }


# @router.get("/jupyter/api/kernelspecs")
# def kernelspecs():
#     return {"default": "flask_kernel", "kernelspecs": {"flask_kernel": {"name": "flask_kernel", "resources": {}, "spec": _kernel_spec}}}


# @router.get("/jupyter/api/kernels")
# @router.post("/jupyter/api/kernels")
# def kernels_normal(request: Request):
#     print(request)
#     data = {
#         "id": "4a8a8c6c-188c-40aa-8bab-3c79500a4b26",
#         "name": "flask_kernel",
#         "last_activity": "2018-01-30T19:32:04.563616Z",
#         "execution_state": "starting",
#         "connections": 0,
#     }
#     return JSONResponse(data, status_code=200)


@router.get("/jupyter/api/kernels/{id}")
async def kernels(id):
    return {"name": "lala", "id": "dsa"}


@router.websocket("/jupyter/api/kernels/{id}/{name}")
async def kernels2(ws: WebSocket, id, name, session_id: Optional[str] = None):
    context_id = ws.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    print("context_id", context_id, id, name, session_id)
    if context_id is None:
        logging.warning(f"no context id cookie set ({appmod.COOKIE_KEY_CONTEXT_ID})")
        await ws.close()
        return
    context = appmod.contexts.get(context_id)
    if context is None:
        logging.warning("invalid context id: %r", context_id)
        await ws.close()
        return

    print("kernels api", id, name)
    kernel = context.kernel
    kernel.shell_stream = WebsocketStreamWrapper(ws, "shell")
    kernel.control_stream = WebsocketStreamWrapper(ws, "control")
    # showtraceback
    import ipywidgets.widgets

    await ws.accept()
    # should we use excepthook ?
    kernel.session.websockets.add(ws)
    print(threading.currentThread())
    with context:
        while True:
            message = await ws.receive()
            if message["type"] == "websocket.disconnect":
                return
            else:
                if "text" in message:
                    msg = json.loads(message["text"])
                else:
                    from jupyter_server.base.zmqhandlers import (
                        deserialize_binary_message,
                    )

                    msg = deserialize_binary_message(message["bytes"])

                msg_serialized = kernel.session.serialize(msg)
                channel = msg["channel"]
                msg_id = msg["header"]["msg_id"]
                if channel == "shell":
                    msg = [BytesWrap(k) for k in msg_serialized]
                    await kernel.dispatch_shell(msg)
                else:
                    print("unknown channel", msg["channel"])


@router.websocket("/solara/watchdog/")
async def watchdog(ws: WebSocket):
    context_id = ws.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    print("watchdog", context_id)
    await ws.accept()
    if context_id is None:
        await ws.send_json({"type": "error", "reason": "no context id found in cookie"})
        await ws.close()
        return
    context = appmod.contexts.get(context_id)
    if context:
        appmod.contexts[context_id].control_sockets.append(ws)
    ok = True
    while ok:
        try:
            if context_id not in appmod.contexts:
                print("closed", context_id)
                await ws.send_json({"type": "reload", "reason": "context id does not exist (server reload?)"})
            else:
                await ws.send_json({"type": "ping", "reason": "check connection"})
            await asyncio.sleep(0.5)
        except websockets.exceptions.ConnectionClosed:
            context = appmod.contexts.get(context_id)
            if context:
                print("closed", context_id)
                context.control_sockets.remove(ws)
            ok = False
            await ws.close()


@router.get("/")
async def read_root(request: Request):
    context_id = request.cookies.get(appmod.COOKIE_KEY_CONTEXT_ID)
    content, context_id = await server.read_root(context_id)
    assert context_id is not None
    response = HTMLResponse(content=content)
    response.set_cookie(appmod.COOKIE_KEY_CONTEXT_ID, value=context_id)
    return response


@router.get("/voila/nbextensions/{dir}/{filename}")
def nbext(dir, filename):
    data = server.nbext(dir, filename)
    if data:
        return Response(data)
    else:
        return Response("not found", status_code=404)


app = FastAPI()
app.include_router(router=router)

# if we add these to the router, the server_test does not run (404's)
app.mount("/static", StaticFiles(directory=directory / "static"), name="static")
app.mount(
    "/solara/static", StaticFiles(directory=f"{sys.prefix}/share/jupyter/nbconvert/templates/lab/static"), name="static"
)

patch.patch()