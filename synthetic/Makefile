SHELL := /bin/bash

PROJECT_ROOT ?= $(PWD)
BUILD_DIR    ?= $(PROJECT_ROOT)/build
OUTPUT_DIR   ?= $(BUILD_DIR)/output
LOG_DIR      ?= $(BUILD_DIR)/logs

OMOP_RAW_DIR ?= $(OUTPUT_DIR)/omop_raw
FHIR_RAW_DIR ?= $(OUTPUT_DIR)/fhir_raw

.PHONY: all generate validate

all: generate validate

generate: generate-omop generate-fhir

generate-omop:
	mkdir -p $(OMOP_RAW_DIR) $(LOG_DIR)
	@echo "[generate-omop] stub"

generate-fhir:
	mkdir -p $(FHIR_RAW_DIR) $(LOG_DIR)
	@echo "[generate-fhir] stub"

validate:
	@echo "[validate] stub"
