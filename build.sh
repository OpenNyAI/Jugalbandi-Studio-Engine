#!/bin/bash

set -e  # Exit on any error

# Ensure top-level dist folder exists and is empty
mkdir -p dist
rm -f dist/*

# Build PwR-NL2DSL
cd ../PwR-NL2DSL
mkdir -p dist
rm -f dist/*
poetry install
poetry build
cd -  # Go back to original directory
cp ../PwR-NL2DSL/dist/*.whl ./dist

# Build PwR-Studio/lib
cd ../PwR-Studio/lib
mkdir -p dist
rm -f dist/*
poetry install
poetry build
cd -
cp ../PwR-Studio/lib/dist/*.whl ./dist

# Build Docker image
echo "Building jbengine:${1}"
docker build . -t jbengine:${1}
