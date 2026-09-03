#!/usr/bin/env python3
import argparse
import asyncio
import logging
import uvicorn
from .main import app
from .discovery import Scanner
from .models import init_db, list_services

logger = logging.getLogger("localdeck.cli")

def main():
    parser = argparse.ArgumentParser(prog="localdeck")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("serve")
    sub.add_parser("scan")
    sub.add_parser("list")
    args = parser.parse_args()
    if args.cmd == "serve":
        init_db()
        uvicorn.run("localdeck.main:app", host="127.0.0.1", port=7575, reload=False)
    elif args.cmd == "scan":
        init_db()
        s = Scanner()
        asyncio.run(s.scan_once())
        print("scan finished")
    elif args.cmd == "list":
        init_db()
        services = list_services()
        print("NAME\tURL\tUPSTREAM")
        for s in services:
            name = s.name or (s.title or "")
            url = f"http://{name if name else '127.0.0.1'}/"
            upstream = f"{s.scheme or 'http'}://{s.host}:{s.port}"
            print(f"{name}\t{url}\t{upstream}")
    else:
        parser.print_help()
