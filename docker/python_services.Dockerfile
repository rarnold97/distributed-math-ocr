FROM python:3.10-slim as python-base

ARG WORKING_DIR=/opt/project
COPY . $WORKING_DIR
WORKDIR $WORKING_DIR

RUN python bootstrap.py --docker-mode

FROM python-base as mathclips-app
RUN python -m build --no-isolation --wheel .
RUN pip list

ARG DEBIAN_FRONTEND="noninteractive"
RUN apt-get update \
    && apt-get install --yes --no-install-recommends xclip xvfb
ENV DISPLAY=:99
RUN nohup bash -c "Xvfb :99 -screen 0 1280x720x16 &"
