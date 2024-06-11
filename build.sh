mkdir -p dist

cd ../NL2DSL-Release && poetry install && poetry build
cd -
cp ../NL2DSL-Release/dist/*.whl ./dist  

cd ../PwR-Studio-Release/lib && poetry install && poetry build
cd -
cp ../PwR-Studio-Release/lib/dist/*.whl ./dist  

docker build -t jbengine:${1} .

