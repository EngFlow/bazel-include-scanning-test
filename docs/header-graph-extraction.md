# Header graphing

We want to be able to determine the graph of header inputs to actions for two reasons:

1. To get some insight into how many header are being pruned from action inputs by include scanning
2. To be able to use the output from comparing action graphs with include scanning turned on and off to inform the
   introduction of `implementation_deps` into a project.

## Generating aquery data

To extract the header graph, we generate aquery data in the jsonproto format. The command used to do for the
llvm-project we ran the command

```bash
bazel aquery --config=generic_gcc  'deps(llvm)' --output=jsonproto
```

Note that the target `llvm` is introduced via [this patch][build-target-patch].
This is needed because the aquery command doesn't play nicely when attempting to directly query the targtets under the
`@llvm-project` external workspace.

## Extracting header graphs

The json file produced above is proccessed using [aquery_header_graph.py][aquery-parsing-script]. This extracts the
header inputs for each build target, and traces back to which target produces the relavant libraries. It's usage is
documented in the script.

[aquery-parsing-script]: ../utils/aquery_header_graph.py
[build-target-patch]: ../benchmark-config/llvm-project/aquery-build-target.patch
