#!/usr/bin/env python3

# Copyright 2016 F-Secure

# Licensed under the Apache License, Version 2.0 (the "License"); you
# may not use this file except in compliance with the License.  You may
# obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.  See the License for the specific language governing
# permissions and limitations under the License.

"""HTTP server acting as an Agent within the guest OS.

The Agent must be installed and executed within the guest OS.

Python 3 is required to run the Agent.

Protocol:

Run a simple command (ls -al on Ubuntu) and collect the output.

curl -X GET localhost:8000/?command=ls%20-al

Upload, execute a file (.pdf on Windows) and collect the output.

curl -X POST --data @document.pdf
   "localhost:8080/?command=acrobat.exe%20\{sample\}&sample=document.pdf"

Same commands without waiting for the output.

curl -X GET "localhost:8000/?command=ls%20-al&async=1"
curl -X POST --data @document.pdf
  "localhost:8080/?command=acrobat.exe%20\{sample\}&sample=document.pdf&async=1"

"""

import os
import json
import logging
import argparse
import subprocess

from tempfile import mkdtemp
from collections import namedtuple
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer


PopenOutput = namedtuple('PopenOutput', ('code', 'log'))


class Agent(BaseHTTPRequestHandler):
    """Serves HTTP requests allowing to execute remote commands."""
    def do_GET(self):
        """Run simple command with parameters."""
        logging.debug("New GET request.")

        query = parse_qs(urlparse(self.path).query)
        command = query['command'][0].split(' ')
        async = bool(int(query.get('async', [False])[0]))
        output = run_command(command, asynchronous=async)

        self.respond(output)

    def do_POST(self):
        """Upload a file and execute a command."""
        logging.debug("New POST request.")

        query = parse_qs(urlparse(self.path).query)
        sample = query['sample'][0]
        async = bool(int(query.get('async', [False])[0]))

        path = self.store_file(mkdtemp(), sample)
        command = query['command'][0].format(sample=path).split(' ')

        output = run_command(command, asynchronous=async)

        self.respond(output)

    def respond(self, output):
        """Generates server response."""
        response = {'exit_code': output.code,
                    'command_output': output.log}

        self.send_response(200)

        self.send_header('Content-type', 'application/json')
        self.end_headers()

        self.wfile.write(bytes(json.dumps(response), "utf8"))

    def store_file(self, folder, name):
        """Stores the uploaded file in the given path."""
        path = os.path.join(folder, name)
        length = self.headers['content-length']

        with open(path, 'wb') as sample:
            sample.write(self.rfile.read(int(length)))

        return path


def run_command(args, asynchronous=False):
    """Executes a command returning its exit code and output."""
    logging.info("Executing %s command %s.",
                 asynchronous and 'asynchronous' or 'synchronous', args)

    process = subprocess.Popen(args,
                               shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)

    try:
        timeout = asynchronous and 1 or None
        output = process.communicate(timeout=timeout)[0].decode('utf8')
    except subprocess.TimeoutExpired:
        pass

    if asynchronous:
        return PopenOutput(None, 'Asynchronous call.')
    else:
        return PopenOutput(process.returncode, output)


def main():
    arguments = parse_arguments()

    logging.basicConfig(level=arguments.debug and 10 or 20)

    logging.info("Serving requests at %s %d.", arguments.host, arguments.port)

    try:
        run_server(arguments.host, arguments.port)
    except KeyboardInterrupt:
        logging.info("Termination request.")


def run_server(host, port):
    server = HTTPServer((host, port), Agent)
    server.serve_forever()


def parse_arguments():
    parser = argparse.ArgumentParser(description='Guest VM Agent.')
    parser.add_argument('host', type=str, help='Server address')
    parser.add_argument('port', type=int, help='Server port')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='log in debug mode')

    return parser.parse_args()


if __name__ == '__main__':
    main()
