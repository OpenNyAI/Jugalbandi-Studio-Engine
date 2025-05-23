#!/bin/bash

# Default environment file
env_file=".env"
JB_ENGINE_VERSION=0.0.1

# Process command-line arguments
while getopts 'e:v:-:' flag; do
  echo "Inside Jugalbandi Manager Configuration for WSL2"
  case "${flag}" in
    e) env_file="${OPTARG}" ;;
    v) JB_ENGINE_VERSION="${OPTARG}" ;;
    -) case "${OPTARG}" in
            stage)
                stage=true
                ;;
            *)
                echo "Unknown option --${OPTARG}" >&2
                exit 1
                ;;
        esac
        ;;
    *) echo "Usage: $0 [-e env_file] [-v JB_ENGINE_VERSION] [service1 service2 ...]"
       exit 1 ;;
  esac
done

# Remove processed options from the arguments list
shift $((OPTIND -1))

# Additional build steps if needed
cd ../../Jugalbandi-Studio-Engine/ && ./build.sh "${JB_ENGINE_VERSION}" && cd -

mkdir -p ../../PwR-Studio/server/dist
cp ../dist/*.whl ../../PwR-Studio/server/dist/

# Create necessary directories
mkdir -p ./media
# mkdir -p ./server/dist

export JBHOST="localhost"
export KAFKA_BROKER="kafka:9092"
export POSTGRES_DATABASE_HOST="postgres"
export PWR_SERVER_HOST="http://server:3000"

# Set other variables
export JB_API_SERVER_HOST="http://localhost:8000"
export JB_ENGINE_VERSION

docker compose build "$@" --build-arg VITE_SERVER_HOST="$JB_API_SERVER_HOST"
# At once place we are using JB_API_SERVER_HOST and at another place we are using from .env-dev
# Here we are not telling it which frontend to build
docker compose --env-file "$env_file" up "$@"
