#!/bin/bash
set -e

# Create jbstudio database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE jbstudio;
EOSQL

echo "jbstudio database created"

# Create jbmanager database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE jbmanager;
EOSQL

echo "jbmanager database created"

# Import jbstudio_dump.sql into jbstudio database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname $STUDIO_POSTGRES_DATABASE_NAME -f /mnt/init/jbstudio_dump.sql

echo "jbstudio_dump.sql imported into jbstudio database"

# Import jbmanager_dump.sql into jbmanager database
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname $MANAGER_POSTGRES_DATABASE_NAME -f /mnt/init/jbmanager_dump.sql

echo "jbmanager_dump.sql imported into jbmanager database"