# Jugalbandi Studio Engine

Jugalbandi Studio Engine provides you an integration between the [Jugalbandi Studio](www.github.com/openyai/jugalbandi-studio) and the [Jugalbandi Manager](www.github.com/openyai/jugalbandi-manager) projects.

Jugalbandi Studio is for building Jugalbandi Apps, built over the [PwR-NL2DSL](https://github.com/microsoft/PwR-NL2DSL) and [PwR-Studio](https://github.com/microsoft/PwR-Studio).
Jugalbandi Manager is for hosting the Jugalbandi Apps build on studio.

This repo provides an integration on how to build and deploy the Jugalbandi Apps on the Jugalbandi Manager. We would run both Studio and Manager together.

## Prerequisites
- [Docker](https://docs.docker.com/get-docker/) (containerization tool)
- [Poetry](https://python-poetry.org/docs/#installation) (Python dependency manager)

## Setup
Below is a concise set of instructions to configure, build, and run the studio and manager.
1. **Clone the Repositories**:
   Clone these 4 repo and ensure they are the same depth
   ```bash
   git clone https://github.com/microsoft/PwR-NL2DSL
   git clone https://github.com/microsoft/PwR-Studio
   git clone https://github.com/OpenNyAI/Jugalbandi-Studio-Engine
   git clone https://github.com/OpenNyAI/Jugalbandi-Manager
   ```
   Arrange them side-by-side in the same folder so your file structure looks like:
   ```
   project-root/
   ├── PwR-NL2DSL/
   ├── PwR-Studio/
   ├── Jugalbandi-Studio-Engine/
   └── Jugalbandi-Manager/
   ```

2. **Configure the Environment**
   - Navigate to `Jugalbandi-Studio-Engine/studio-and-manager`.
   - Copy `.env.template` to `.env`:
     ```bash
     cp .env.template .env
     ```
   - Open `.env` and fill in the required variables. If you **only** need the Studio, set values for `# PwR Studio` and `# LLM Credentials`. If you also want the Manager, include the `# Language` values.

3. **Run the Application**
   - To build and run **only the Studio**:
     ```bash
     bash scripts/run.sh studio engine server
     ```
   - To run the **Manager alongside the Studio**:
     ```bash
     bash scripts/run.sh server engine studio api channel language flow frontend
     ```

     Note: If using AzureOpenAI with Azure credentials, you will be prompted twice to sign in. Follow the instructions on the terminal to proceed.

5. **Access the Studio**
   - Open [http://localhost:4173](http://localhost:4173) in your browser to access the studio.

**Support**

For issues or questions, visit our [GitHub Issues](https://github.com/OpenNyAI/Jugalbandi-Studio-Engine/issues) page or contact the maintainers.

