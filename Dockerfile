
FROM mcr.microsoft.com/mirror/docker/library/python:3.11-slim as builder

RUN pip install poetry==1.7.1

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /app
COPY ./pyproject.toml ./poetry.lock ./
# poetry needs a README.md to build the project
RUN touch README.md 

RUN poetry install && rm -rf $POETRY_CACHE_DIR



FROM mcr.microsoft.com/mirror/docker/library/python:3.11-slim as runtime

ENV VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY . .

# run the below command if the environment variable PWR_ENGINE is set to 'typechat'
# RUN if [ "$PWR_ENGINE" = "TypeChat" ]; then pip install --no-cache-dir ./verified-jb-app/typechat-0.0.1-py3-none-any.whl; fi
# RUN pip install --no-cache-dir ./typechat-0.0.1-py3-none-any.whl

# install all wheels in the dist folder
RUN pip install --no-cache-dir ./dist/*.whl

CMD ["python", "-u", "-m", "main"]
