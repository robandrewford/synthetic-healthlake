#!/usr/bin/env python3
import argparse
import yaml
import pandas as pd
from pathlib import Path

def load_yaml(path: Path):
    with path.open() as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--omop-dir', required=True)
    parser.add_argument('--fhir-dir', required=True)
    parser.add_argument('--constraints-config', required=True)
    parser.add_argument('--distributions-config', required=True)
    parser.add_argument('--terminology-dir', required=True)
    args = parser.parse_args()
    print("Stub apply_domain_constraints: omop-dir", args.omop_dir)

if __name__ == "__main__":
    main()
