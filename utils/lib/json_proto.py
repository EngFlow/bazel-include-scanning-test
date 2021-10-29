"""A module to read bazel's json-proto stuff.

This looks like so:

```
{
    "key": "Totally valid JSON"
}{
    "however": "JSON doesn't actually support multiple top level objects"
}
```

I don't know why this is the chosen output format, but we'll have to work with it.
"""

import json
from typing import Any, Dict, List, TextIO

JSONProto = List[Dict[str, Any]]


def load(infile: TextIO) -> JSONProto:
    """Load the given jsonproto file.

    TODO: Currently, the implementation is quite naive. It's possible
    we'll discover that this needs too much memory to parse large
    graphs, in which case this will need to do some chunk reading.
    """

    # Chop off the first `{` and the last `}` so we can more easily
    # fix that later.
    raw = infile.read()[1:-1]

    return [json.loads('{' + proto + '}') for proto in raw.split("}{")]
