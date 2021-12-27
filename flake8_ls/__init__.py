#
# Copyright (c) 2021 Mehdi Abaakouk <sileht@sileht.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import argparse
import contextlib
import io
import re
import time
import typing

from flake8.main import application
from pygls import server
from pygls.lsp import methods
from pygls.lsp import types


class redirect_stdin(contextlib.redirect_stdout):  # type: ignore
    _stream = "stdin"


FLAKE8_OUTPUT_RE = re.compile(
    r"(?P<file>[^:]+):(?P<row>[-+]?\d+):(?P<col>[-+]?\d+): (?P<code>[^ ]+) (?P<message>.*)"
)
FLAKE8_SEVERITY = {
    "E": types.DiagnosticSeverity.Error,
    "W": types.DiagnosticSeverity.Warning,
    "F": types.DiagnosticSeverity.Information,
    "D": types.DiagnosticSeverity.Information,
    "R": types.DiagnosticSeverity.Warning,
    "S": types.DiagnosticSeverity.Warning,
    "I": types.DiagnosticSeverity.Warning,
    "C": types.DiagnosticSeverity.Warning,
    "B": types.DiagnosticSeverity.Warning,
}


class Flake8Server(server.LanguageServer):
    def __init__(self) -> None:
        super().__init__()
        self._debug = False
        self._flake8 = application.Application()
        self._flake8.initialize(["--format", "default", "--no-show-source"])

    def set_debug(self, debug: bool) -> None:
        self._debug = debug

    async def validate(
        self,
        params: typing.Union[
            types.DidOpenTextDocumentParams,
            types.DidChangeTextDocumentParams,
            types.DidSaveTextDocumentParams,
        ],
    ) -> None:
        text_doc = self.workspace.get_document(params.text_document.uri)
        stderr = io.BytesIO()
        stdout = io.BytesIO()
        stdin = io.BytesIO(text_doc.source.encode())
        with contextlib.redirect_stderr(
            io.TextIOWrapper(stderr)
        ), contextlib.redirect_stdout(io.TextIOWrapper(stdout)), redirect_stdin(
            io.TextIOWrapper(stdin)
        ):
            started_at = time.monotonic()
            self._flake8.run_checks(["-"])
            self._flake8.report()
            elapsed = time.monotonic() - started_at

            out = stdout.getvalue().decode()
            err = stderr.getvalue().decode()

        if self._debug:
            self.show_message(f"Ran flake8 in {elapsed}s:")
            self.show_message(f"* uri: {text_doc.uri}")
            self.show_message(f"* stdout: {out}")
            self.show_message(f"* stderr: {err}")

        lines = [line.strip() for line in out.split("\n") if line.strip()]
        diagnostics = []
        for line in lines:
            m = FLAKE8_OUTPUT_RE.match(line)
            if m is None:
                self.show_message(f"fail to parse mypy result: {line}")
                self.show_message_log(f"fail to parse mypy result: {line}")
            else:
                data = m.groupdict()
                row = int(data["row"])
                col = int(data["col"])
                d = types.Diagnostic(
                    range=types.Range(
                        start=types.Position(line=row - 1, character=col - 1),
                        end=types.Position(line=row - 1, character=col),
                    ),
                    message=data["message"],
                    code=data["code"],
                    severity=FLAKE8_SEVERITY.get(
                        data["code"][0], types.DiagnosticSeverity.Warning
                    ),
                    source="flake8-ls",
                )
                diagnostics.append(d)

        self.publish_diagnostics(text_doc.uri, diagnostics)


ls = Flake8Server()


@ls.feature(methods.TEXT_DOCUMENT_DID_OPEN)
async def did_open(self: Flake8Server, params: types.DidOpenTextDocumentParams) -> None:
    await self.validate(params)


@ls.feature(methods.TEXT_DOCUMENT_DID_CHANGE)
async def did_change(
    self: Flake8Server, params: types.DidChangeTextDocumentParams
) -> None:
    await self.validate(params)


@ls.feature(methods.TEXT_DOCUMENT_DID_SAVE)
async def did_save(self: Flake8Server, params: types.DidSaveTextDocumentParams) -> None:
    await self.validate(params)


def main() -> None:
    parser = argparse.ArgumentParser(description="super fast mypy language server")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    ls.set_debug(args.debug)
    ls.start_io()  # type: ignore[no-untyped-call]
