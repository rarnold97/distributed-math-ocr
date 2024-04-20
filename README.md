# Intro

Fundamentally, this software will take an input mathematical symbol image, convert it to Latex, using backend OCR ML algorithms,
and then render the converted Latex sequence in a web-formatted view for the user.  All of this is accomplished using IPC and distributed system protocols.

> DISCLAIMER: This project is an open-sourced project, originally inspired by [@rarnold97](https://github.com/rarnold97)
  for the purposes of graduate academic study.

This application is meant to be a web-based, distributed application that encourages team usage and collaboration.
The target audience of this application is technical professionals and university students.  The following are potential applications of this software:

- University STEM course note-taking
- University Group Project tool
- Exam equation sheet generator
- professional tool for grant/proposal writing
- professional collaborative note-taking and documentation tool

# Running the Software

## Docker Compose

Deploying the app with the docker-compose cli is simple, run:

```bash
docker-compose up
```

Although, it is recommended to allow the RabbitMQ and MongoDB services fully start up before running the python services. Also, sometimes using run for the backend Python services is more successful.
You can also try:

```bash
docker-compose up mongo-express rabbitmq
...
docker-compose up frontend
docker-compose run ingest ml_pipeline
```

## Manual for Development

To run all of the services locally, I recomend runnning the python modules accordingly.

> NOTE: The Mongo and RabbitMQ services will still be deployed via docker-compose.  The Python services should be ran in separated processes/terminals.

To create a virtual environment, and install all required dependencies within a `.venv` folder, run:

```bash
python bootstrap.py
```

Then, you can proceed by running:

```bash
docker-compose build mongo-express rabbitmq
docker-compose up mongo-express rabbitmq
python -m mathclips.services.ingest
python -m mathclips.services.image_to_equation_interface
cd mathclips/front_end
streamlit run app.py
```

# Architecture

## Technologies Used

| Technology | Application |
| --- | --- |
| Protobuf | RPC |
| Mongo | Database (store image entries with equations formatted) |
| Python | ML/OCR |
| streamlint | web applications |
| LaTex | mathematical Rendering |
| HTML | render latex equations |
| Docker | For Service Abstractions |
| Kubernetes | Service Scaling / Distributed Optimization |
| Python | Middleware Programming |
| Rabbit MQ / C++ | Message Broker |

## Network Architecture

The network flow is roughly outlined int the [docker-compose.yml](./docker-compose.yml) file.  The idea is that there should be two networks:
1. a backend Network
2. a frontend network

The Frontend network would be where clients would primarily interface.  This could be viewed and interacted with by multiple clients, and all requests would be transmitted to the backend.
The frontend primarily consists of a streamlit web-app, that sends requests through Rabbit MQ and has access to a mongo Database.

The backend network is where all the requests are handled, and delivered to by RabbitMQ.  This primarily consists of ML eval and training pipelines. When the ML piepline produces a result,
A shared config (think of this as a PIPE almost) is maintained and modified, which the frontend can access and render.  The data within the config is cached to the backend, so it can be preserved, even if the shared config file were to be modified. (This shared config is currently localted at [`default_session_equation_sections.yml](./mathclips/services/front_end/default_session_equation_sections.yml)).

### Ingest Service
The ingest service is primarily a listener, that is subscribed to ML Pipeline Result messages, and train request messages.  In the case of a Result message, the database will be updated with the result, and a shared YAML config file is modified with the data, and subsequently rendered by the frontend.  If the ingest service receives train requests, it will first mark the appropriate record in the database with a flag that it will be used for training data.  The user is responsible for reporting the correct label throught the web UI.  This label is also stored in the database. If enough records are marked as training samples, then a training ML Model pipeline is kicked off, and the weights for the model are then updated.  The weights from each batch are also stored in the database.

### ML Pipeline Service
The ML pipeline service triggers in response to image uploads by the user.  The service will receive an `Image` protobuf message. From the message, the actual image data can be queried from the file storage component of the database. Using the image, the model evaluates it and makes a Latex equation prediciton.  The prediction is then stored to the database, and then wrapped back into a protobuf for further processing the by the ingest service.  This entails manipulating the data in a way that can be rendered by the Streamlit frontend service.

# Development

## Scaling to Remote Hosts / Kubernetes

Currently, this software is scalable.  This is largely possible due to the RabbitMQ worker queue paradigm.
Furthermore, by using the `prefetch` option int QOS settings, this software is able to employ round-robbin scheduling
to delegate workloads.  No complicated exchanges are currently being employed. The RabbitMQ setup is based on the source documentation example
at [RabbitMQ Work Queue Documentation](https://www.rabbitmq.com/tutorials/tutorial-two-python).  The python services make use of the `multiprocessing`
library to deploy mulitple workers to handle queue messages ingestion.  For a prototype, this is mostly set to two worker processes per service block.
To extend this, you can change module variables in the [`mathclips/services/__init__.py](./mathclips/services/__init__.py) module interface.
This can be accomplished through the `mathclips` API programmatically by doing the following:

```python
import mathclips

mathclips.services.NUM_TRAIN_WORKERS = 10 # going from: 2 -> 10
mathclips.services.kNUM_ML_PIPELINES = 2 # going from: 2 -> 10
mathclips.services.kNUM_RESULT_WORKERS = 1 # going from: 1 -> 5
```

This is a useful feature when deploying and scaling for a large-scale application.  The bottleneck process is most likely going to be the training queue/pipeline, so take
that into account when designing/scaling a hosted system.

## ML OCR Model Development and Current Limitations

This software supports a training feedback loop, where users can designate an equation as incorrect and relabel it.  When doing so, the backend ingest service will mark
the corresponding record in the provided Mongo DB with:

- the new training label
- a flag that it needs to be trained

The database will keep collecting this information, until the minimum train + validation threshold is breached.  What this means, is there needsd to be a sufficient amount of
records marked with: `needs_train`, in order to kickoff a training pipeline.  The threshold needs to be sufficiently large enough to produce sensible weights and checkpoints for an updated model.  Otherwise, the produced weights will be ignored, in favor of the default checkpoints and weights provided by the original author of the OCR/ML library for latex equation image recognition. The setting for this threshold is located at: [`mathclips/services/__init__.py`](./mathclips/services/__init__.py), and can be configured through: `MIN_TRAIN_BATCH_SIZE`.

```python
import mathclips

mathclips.services.MIN_TRAIN_BATCH_SIZE = 64
```

> NOTE: the validation size is either half the training batch size, or 20% of the batch size, depending on how small the training batch size is.


With the limited testing I have done, I was only able to assemble a handful of training images.  In a high-fidelity Machine Learning model, you likely need thousands of
input samples to effectively train/retrain a model. Therefore, I was getting bad performance during training and weights updates.  Therfore, I programmed the software
to prefer the original weights, if training did not produce a better model. The details of this can be located in the [ingest service](./mathclips/services/ingest.py).