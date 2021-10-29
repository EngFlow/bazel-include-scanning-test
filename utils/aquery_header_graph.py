#!/usr/bin/env python3
"""
This script takes a bazel action graph and produces a graph of build targets based on their
header inputs. The output is a list of targets, annotated with the header inputs used by each
target, and which targets the header originate from.

Usage: ./aquery_header_graph.py <aquery_input_file> [<target_prefix>]

<aquery_input_file> A file containing the output from a bazel aquery with
                    `--output=jsonproto`
<target_prefix>     The script will only output targets which match this prefix.
                    Optional, defaults,to "//".
"""
import argparse
import functools
import sys
import json

from typing import Callable, Dict, Iterable, NoReturn, Set, Union, List
from functools import lru_cache
from pathlib import Path


class Aquery:
    path_fragments: dict
    artifacts: dict
    depsets: dict
    targets: dict
    actions: dict

    def __init__(self, file):
        with open(file, "r") as f:
            print(f"Parsing aquery from {file}", file=sys.stderr)
            raw_aquery = json.load(f)

        self.path_fragments = {item["id"]: item for item in raw_aquery["pathFragments"]}
        self.artifacts = {item["id"]: item for item in raw_aquery["artifacts"]}
        self.depsets = {item["id"]: item for item in raw_aquery["depSetOfFiles"]}
        self.targets = {item["id"]: item for item in raw_aquery["targets"]}
        self.actions = [item for item in raw_aquery["actions"]]

    @lru_cache(maxsize=None)
    def _flatten_depset(self, depset_id: int) -> Set[int]:
        """
        Flatten a depset into a set of artifact ids including all direct and transitive dependencies.
        """
        depset = self.depsets[depset_id]

        artifact_ids = set(depset.get("directArtifactIds", set()))
        transitive_depsets = depset.get("transitiveDepSetIds", [])
        if not transitive_depsets:
            return artifact_ids
        else:
            for id in transitive_depsets:
                artifact_ids.update(self._flatten_depset(id))

        return artifact_ids

    def get_all_header_deps(self, action: dict) -> Set[int]:
        """
        Determine all .h inputs into an action, returning a set of artifact ids
        """
        all_deps = self.get_all_inputs(action)
        header_deps = filter(
            lambda artifact_id: self.get_filename(artifact_id).endswith(".h"),
            all_deps,
        )
        return set(header_deps)

    def get_direct_inputs(self, action: dict) -> Set[int]:
        inputs = set()
        for id in action.get("inputDepSetIds", set()):
            depset = self.depsets[id]
            direct_inputs = depset["directArtifactIds"]
            inputs.update(direct_inputs)
        return inputs

    def get_transitive_inputs(self, action: dict) -> Set[int]:
        transitive_depsets = set()
        for id in action.get("inputDepSetIds", set()):
            depset = self.depsets[id]
            transitive_depsets.update(depset.get("transitiveDepSetIds", []))
        transitive_inputs = set()
        for id in transitive_depsets:
            transitive_inputs.update(self._flatten_depset(id))
        return transitive_inputs

    def get_all_inputs(self, action: dict) -> Set[int]:
        """
        Determine the set of all direct and transitive inputs for an action
        """
        all_deps = set()
        for id in action.get("inputDepSetIds", set()):
            all_deps.update(self._flatten_depset(id))

        return all_deps

    def get_filename(self, artifact_id: int) -> str:
        artifact_path_fragment_id = self.artifacts[artifact_id]["pathFragmentId"]
        return self.path_fragments[artifact_path_fragment_id]["label"]

    def get_full_filename(self, artifact_id: int) -> str:
        artifact = self.artifacts[artifact_id]

        fragment_id = artifact["pathFragmentId"]
        fragment = self.path_fragments[fragment_id]
        name_fragments = [fragment["label"]]
        parent_id = fragment.get("parentId", None)
        while parent_id:
            parent = self.path_fragments[parent_id]
            name_fragments = [parent["label"], *name_fragments]
            parent_id = parent.get("parentId", None)

    def get_filenames(self, artifact_ids: Iterable[int]) -> List[str]:
        return [self.get_filename(id) for id in artifact_ids]

    def get_target_label(self, targetId: int) -> str:
        if targetId is not None:
            return self.targets[targetId]["label"]
        else:
            return str(targetId)

    def get_action_outputs(self, action: Dict) -> Set[int]:
        return set(action["outputIds"])

    @functools.lru_cache(maxsize=None)
    def get_artifact_source(self, artifact_id: int) -> Union[str, NoReturn]:
        """
        Determine's which bazel target outputs a given artifact.
        """
        for action in self.actions:
            if artifact_id in self.get_action_outputs(
                action
            ) and self.get_action_target(action):
                target = self.get_action_target(action)
                return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=Path, nargs=1)
    parser.add_argument(
        "--target_prefix", type=str, required=False, default="//", nargs=1
    )
    parser.add_argument(
        "--anonymous",
        required=False,
        default=False,
        action="store_true",
    )
    args = parser.parse_args()
    target_prefix: str = args.target_prefix[0]
    input_file: Path = args.input_file[0]

    aquery = Aquery(input_file)

    # Group together actions by the bazel targets they are part of. There's some
    # stuff going on with "middleman" actions which makes considering them as individual
    # actions awkward.
    targets: Dict[int, Dict] = dict()
    for action in aquery.actions:
        target_label = action["targetId"]
        all_inputs = aquery.get_all_inputs(action)
        action_outputs = aquery.get_action_outputs(action)

        direct_inputs = aquery.get_direct_inputs(action)
        transitive_inputs = aquery.get_transitive_inputs(action)

        target = targets.get(target_label, None)
        if target:
            target["all_inputs"].update(all_inputs)
            target["direct_inputs"].update(direct_inputs)
            target["transitive_inputs"].update(transitive_inputs)
            target["outputs"].update(action_outputs)
            target["action_counter"] += 1
        else:
            targets[target_label] = {
                "all_inputs": all_inputs,
                "direct_inputs": direct_inputs,
                "transitive_inputs": transitive_inputs,
                "outputs": action_outputs,
                "action_counter": 1,
            }

    # Now munge the data into a sensible output format
    processed_targets: List[Dict] = []
    for key, target in targets.items():

        all_inputs = list(target["all_inputs"])
        only_headers: Callable[[List[int]], List[int]] = lambda ids: [
            id for id in ids if aquery.get_filename(id).endswith(".h")
        ]
        header_inputs = only_headers(all_inputs)

        direct_inputs = list(target["direct_inputs"])
        direct_header_inputs = only_headers(direct_inputs)

        transitive_inputs = list(target["transitive_inputs"])
        transitive_header_inputs = only_headers(transitive_inputs)

        outputs = list(target["outputs"])
        header_outputs = only_headers(outputs)

        # Now replace target entry with desired_data
        processed_targets.append(
            {
                "targetId": key,
                "header_output_ids": header_outputs,
                "header_input_ids": header_inputs,
                "transitive_header_inputs": transitive_header_inputs,
                "direct_header_inputs": direct_header_inputs,
                "action_count": target["action_counter"],
            }
        )

    # Now loop through for the header provenencing
    output = []
    for target in processed_targets:

        def provenence_header_file(
            targets: List[Dict], header_id: int
        ) -> Union[int, None]:
            for target in targets:
                if header_id in target["direct_header_inputs"]:
                    header_source = target["targetId"]
                    return header_source
            return None

        header_ids = target["transitive_header_inputs"]
        header_providing_dependencies = {
            provenence_header_file(processed_targets, id)
            for id in target["transitive_header_inputs"]
        }

        header_providing_dependencies.discard(None)
        target["header_providing_deps"] = list(header_providing_dependencies)

        def should_output_target(target) -> bool:
            involves_headers = target.get("header_input_ids") or target.get(
                "header_output_ids"
            )
            matches_target_filter = args.anonymous or aquery.get_target_label(
                target["targetId"]
            ).startswith(target_prefix)

            return involves_headers and matches_target_filter

        if should_output_target(target):
            target_label = target["targetId"]
            header_inputs = target["header_input_ids"]

            header_inputs_by_source_target = dict()
            for id in header_inputs:
                source_target = provenence_header_file(processed_targets, id)
                exisiting_headers = header_inputs_by_source_target.get(
                    source_target, []
                )
                header_inputs_by_source_target[source_target] = exisiting_headers + [id]

            # If we're not using anonymous data, then do a last minute evaluation of names
            if not args.anonymous:
                target_label = aquery.get_target_label(target_label)
                header_inputs = aquery.get_filenames(header_inputs)
                header_inputs_by_source_target = {
                    aquery.get_target_label(target): aquery.get_filenames(headers)
                    for target, headers in header_inputs_by_source_target.items()
                }

            output.append(
                dict(
                    label=target_label,
                    header_inputs=header_inputs_by_source_target,
                )
            )

    json.dump(output, sys.stdout, indent=2)
