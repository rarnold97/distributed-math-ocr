# cache the image database and ml weights
# namespace class
# adding to init to avoid circular referencing
class IngestQueueNames:
    RESULT_QUEUE: str = "ml_result"
    TRAIN_QUEUE: str = "training_queue"
    ML_PIPELINE_QUEUE: str = "ml_pipeline"

# TODO - Make these configurable
MIN_TRAIN_BATCH_SIZE: int = 2
NUM_TRAIN_WORKERS: int = 2
NUM_ML_PIPELINES: int = 2
NUM_RESULT_WORKERS: int = 1

# to enable localhost while debugging, set to True
LOCAL_MODE: bool = True
#LOCAL_MODE: bool = False