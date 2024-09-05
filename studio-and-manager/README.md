# Jugalbandi Studio Engine

Jugalbandi Studio Engine provides you an integration between the [Jugalbandi Studio](www.github.com/openyai/jugalbandi-studio) and the [Jugalbandi Manager](www.github.com/openyai/jugalbandi-manager) projects.

Jugalbandi Studio is for building Jugalbandi Apps, built over the PwR-NL2DSL and PwR-Studio.
Jugalbandi Manager is for hosting the Jugalbandi Apps build on studio.

This repo provides an integration on how to build and deploy the Jugalbandi Apps on the Jugalbandi Manager. We would run both Studio and Manager together.

## Setup
1. Clone these 4 repo and ensure they are the same depth:
   1. [Jugalbandi Studio Engine](https://github.com/OpenNyAI/Jugalbandi-Studio-Engine/)
   2. [Jugalbandi Manager](https://github.com/OpenNyAI/Jugalbandi-Manager/)
   3. [PwR-Studio](https://github.com/microsoft/PwR-Studio)
   4. [PwR-NL2DSL](https://github.com/microsoft/PwR-NL2DSL/)
2. Ensure you have [poetry installed](https://python-poetry.org/docs/#installing-with-pipx)
```bash
poetry --version
```
3. Ensure you have the right values for `.env-dev`
```bash
cp .env-dev.template .env-dev
```
5. Go inside the `studio-and-manager` directory. 
```bash 
$ cd studio-and-manager
```
8. Run the following command.
```bash
$ bash scripts/run.sh server engine studio api channel language flow frontend
```
9. Go to http://localhost:4173 to access Jugalbandi Studio.
10. Go to http://localhost:4179 to access Jugalbandi Manager.
