#!/usr/bin/env python3

"""Implementation deps emulation script.

This takes output from `aquery_header_graph.py`, one from a build
without include scanning, and one from a build with include scanning.

The script then uses the information of which headers could be pruned
by include scanning to infer which libraries could be moved to
implementation_deps, and whose headers would therefore be pruned from
the graph, to calculate the number of headers that would be pruned by
optimal use of implementation deps.
"""


import argparse
import json
from typing import Any, Dict, List, Set


def compare(default: List[Dict[str, Any]], scanned: List[Dict[str, Any]]):
    used_headers: Dict[str, Set[str]] = {}
    used_headers_post: Dict[str, Set[str]] = {}

    for proto in default:
        header_inputs: Dict[str, List[str]] = proto["header_inputs"].items()

        for dep, headers in header_inputs:
            if dep not in used_headers:
                used_headers[dep] = set(headers)
            else:
                used_headers[dep] &= set(headers)

    for proto in scanned:
        header_inputs: Dict[str, List[str]] = proto["header_inputs"].items()

        for dep, headers in header_inputs:
            if dep not in used_headers_post:
                used_headers_post[dep] = set(headers)
            else:
                used_headers_post[dep] &= set(headers)

    headers_unscanned = set().union(*used_headers.values())
    headers_scanned = set().union(*used_headers_post.values())

    print("Unmodified header count:", len(headers_unscanned))
    print(
        "After include scanning:",
        len(headers_unscanned)
        - (
            len(headers_unscanned - headers_scanned)
            - len(headers_scanned - headers_unscanned)
        ),
    )

    removed_libs = list(
        filter(lambda lib: lib[0] not in used_headers_post, used_headers.items())
    )
    print(
        "After implementation deps (simulated):",
        len(headers_unscanned) - sum(len(lib[1]) for lib in removed_libs),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("default_graph", type=argparse.FileType("r"))
    parser.add_argument(
        "include_scanning_graph",
        type=argparse.FileType("r"),
    )
    args = parser.parse_args()

    compare(json.load(args.default_graph), json.load(args.include_scanning_graph))


if __name__ == "__main__":
    main()
