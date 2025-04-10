rm -f dist/* && mkdir -p dist
cd ../PwR-NL2DSL && rm dist/* && poetry install && poetry build && cd - && cp ../PwR-NL2DSL/dist/*.whl ./dist
cd ../PwR-Studio/lib && rm dist/* && poetry install && poetry build && cd - && cp ../PwR-Studio/lib/dist/*.whl ./dist

echo "Building jbengine:${1}"
docker build -t jbengine:${1} .
