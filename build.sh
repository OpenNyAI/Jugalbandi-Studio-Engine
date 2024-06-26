mkdir -p dist

cd ../Jugalbandi-Manager/jb-manager-bot && poetry install && poetry build
cd -
cp ../Jugalbandi-Manager/jb-manager-bot/dist/*.whl ./dist

cd ../PwR-NL2DSL && poetry install && poetry build
cd -
cp ../PwR-NL2DSL/dist/*.whl ./dist  

cd ../PwR-Studio/lib && poetry install && poetry build
cd -
cp ../PwR-Studio/lib/dist/*.whl ./dist  

echo "Building jbengine:${1}"
docker build -t jbengine:${1} .
