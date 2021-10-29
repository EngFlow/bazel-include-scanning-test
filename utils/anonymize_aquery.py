#!/usr/bin/env python3

import json
import sys
from typing import Dict

if __name__ == "__main__":
    input_file = sys.argv[1]
    with open(input_file, 'r') as f:
        aquery : Dict = json.load(f)

    # This will eventually be our anonymised aquery data
    anonymised = dict()
    # artifacts
    # {
    #    id: int
    #    pathFragmentId: int
    # }
    # This field has nothing to anonymise
    anonymised["artifacts"] = []
    for artifact in aquery["artifacts"]:
        anonymised_artifact = {
            "id": artifact["id"],
            "pathFragmentId": artifact["pathFragmentId"],
        }
        anonymised["artifacts"].append(anonymised_artifact)

    # actions
    # {
    #   targetId: int
    #   actionKey: str
    #   arguments: List[str]
    #   mnemonic: str
    #   configurationId: int
    #   inputDepsetIds: List[int]
    #   outputIds: List[int]
    #   primaryOutputId: int
    #   executionPlatform: str
    # }
    anonymised["actions"] = []
    for action in aquery["actions"]:
        anonymised_action = {}
        for key in ["targetId", "inputDepSetIds", "outputIds", "primaryOutputId"]:
            if key in action:
                anonymised_action[key] = action[key]
        anonymised["actions"].append(anonymised_action)

    # targets
    # {
    #   id: int
    #   label: str
    #   ruleClassId: int
    # }
    anonymised["targets"] = []
    for target in aquery["targets"]:
        anonymised_target = {
            "id": target["id"],
            "label": str(target["id"]),
        }
        anonymised["targets"].append(anonymised_target)

    # depSetOfFiles
    # {
    #   id: int
    #   transitiveDepSetIds: List[int]
    #   directArtifactIds: List[int]
    # }
    # This field has nothing to anonymise
    anonymised["depSetOfFiles"] = []
    for depSet in aquery["depSetOfFiles"]:
        anonymised_depset = {
            "id": depSet["id"],
            "transitiveDepSetIds": depSet.get("transitiveDepSetIds", []),
            "directArtifactIds": depSet.get("directArtifactIds", []),
        }
        anonymised["depSetOfFiles"].append(anonymised_depset)


    # configuration
    # {
    #   id: int
    #   mnemonic: str
    #   platformName: str
    #   checksum: str
    # }
    # We're not interested in this field, omit it entirely

    # rule classes
    # {
    #   id: int
    #   name: str
    # }
    # We're not interested in this field, omit it entirely

    # path fragments
    # {
    #   id: int
    #   label: str
    #   parentId: int
    # }
    anonymised["pathFragments"] = []
    for fragment in aquery["pathFragments"]:
        # Anonymise the label, preserving only whether the fragment refers to a header file or not
        label = fragment["label"]
        if label.endswith(".h"):
            anon_label = str(fragment["id"]) + ".h"
        else:
            anon_label = str(fragment["id"])

        anonymised_fragment = {
            "id": fragment["id"],
            "label": anon_label,
        }
        anonymised["pathFragments"].append(anonymised_fragment)

    json.dump(anonymised, sys.stdout, indent=0)
