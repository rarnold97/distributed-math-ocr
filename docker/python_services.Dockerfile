#FROM python:3.10-slim as python-base

# Configure Poetry
# ENV POETRY_VERSION=1.7.1
# ENV POETRY_HOME=/opt/poetry
# ENV POETRY_VENV=/opt/poetry-venv
# ENV POETRY_CACHE_DIR=/opt/.cache

#FROM python-base as poetry-base

# Install poetry separated from system interpreter
# RUN python3 -m venv $POETRY_VENV \
#     && $POETRY_VENV/bin/pip install -U pip setuptools \
#     && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}

#FROM python-base as mathclips-app
FROM python:3.10-slim as python-base

# Copy Poetry to app image
#COPY --from=poetry-base ${POETRY_VENV} ${POETRY_VENV}
# Add Poetry to PATH
#ENV PATH="${PATH}:${POETRY_VENV}/bin"

ARG WORKING_DIR=/opt/project
COPY . $WORKING_DIR
WORKDIR $WORKING_DIR

# Poetry way of doing things
# RUN poetry config virtualenvs.create false
# RUN poetry install --with build
# RUN poetry build -f wheel
# RUN pip install --find-links dist/ mathclips
# # preinstall pix2tex default ML checkpoints and weights
# RUN python -m pix2tex.model.checkpoints.get_latest_checkpoint
RUN python bootstrap.py --docker-mode

ARG WORKING_DIR=/opt/project
WORKDIR $WORKING_DIR

FROM python-base as mathclips-app
RUN python -m build --no-isolation --wheel .
#RUN pip install --find-links dist/ mathclips
RUN pip list
