from __future__ import annotations

from typing import List, Dict, TypeAlias
import clipboard
from pathlib import Path
import uuid
import datetime

import streamlit as st
from streamlit.delta_generator import DeltaGenerator
import yaml
import pymongo
from pymongo.database import Database
from munch import Munch

import mathclips.front_end
from mathclips.services.rmq import publish_proto_message
from mathclips.services import IngestQueueNames
from mathclips.services.ingest import default_result_config_filename
from mathclips.services.logger import logger
from mathclips.services.mongodb import MathSymbolResultDatabase
from mathclips.proto.pb_py_classes.image_pb2 import Image as ProtoImage
from mathclips.proto.pb_py_classes.ocr_result_pb2 import OCR_Result
from mathclips.proto.pb_py_classes.uint_packed_bytes_pb2 import UintPackedBytes as UintPacked
from mathclips.proto.pb_py_classes.train_pb2 import TrainRequest
import mathclips

IdType: TypeAlias = str | int

mathclips_root_dir = Path(mathclips.__path__[0]).resolve()
front_end_dir = mathclips_root_dir / "front_end"
default_config_filename = mathclips.front_end.notebook_config_path
print(default_config_filename)

st.set_page_config("Math Equation Notebook",
                   page_icon = str(front_end_dir / "static" / "mathclips_logo_small.png"))

@st.cache_resource
def init_mongo_db_connection():
    return pymongo.MongoClient(**st.secrets["mongo"])

@st.cache_resource
def init_result_database(_db: Database):
    return MathSymbolResultDatabase(_db)

mongo_client = init_mongo_db_connection()
db: Database = mongo_client["mathclips_data"]
result_db = init_result_database(db)

def get_config_file_timestamp(config_filename: Path = default_config_filename):
    return datetime.datetime.fromtimestamp(config_filename.stat().st_mtime)

def on_equation_copy(latex_equation: str):
    clipboard.copy(latex_equation)
    st.toast(body = f"Successfully Copied: {latex_equation}", icon = "✅")

def on_delete_click(result: OCR_Result, widget_keys: List[IdType]):
    section_config = st.session_state.section_config_data
    database_id: UintPacked = None
    if result.input_image_data.parent_section in section_config:
        if result.input_image_data.equation_name in section_config[result.input_image_data.parent_section]:
            database_id = UintPacked(\
                first_bits = int(section_config[result.input_image_data.parent_section][result.input_image_data.equation_name]\
                    ["db_id"]["first_bits"]),
                last_bits = int(section_config[result.input_image_data.parent_section][result.input_image_data.equation_name]\
                    ["db_id"]["last_bits"]))
            del section_config[result.input_image_data.parent_section][result.input_image_data.equation_name]

    for widget_key in widget_keys:
        if widget_key in st.session_state:
            del st.session_state[widget_key]

    if not bool(section_config[result.input_image_data.parent_section]):
        # remove page if completely empty
        del section_config[result.input_image_data.parent_section]

    result_db.delete(database_id)

    # reconstruct the config file after removing relevant section data
    with open(default_config_filename, 'w') as config_file:
        yaml.safe_dump(section_config, config_file)

    st.toast(body = f"Successfully Removed: {result.input_image_data.equation_name}", icon = "✅")

def on_train_click(result_uid: UintPacked):
    if "train_label" in st.session_state:
        train_latex_label = st.session_state.train_label
        if train_latex_label:
            train_message = TrainRequest(result_uid = result_uid,
                                         latex_str = train_latex_label)
            # publish train message to queue
            publish_proto_message(train_message, IngestQueueNames.TRAIN_QUEUE)
            st.toast(body = "Logged Result to be marked for ML Training", icon = "🏋️‍♂️")

def add_equation_result(result: OCR_Result) -> DeltaGenerator:
    container = st.container(border = True)
    container.subheader(body = result.input_image_data.equation_name, divider = "blue")
    container.latex(rf"{result.latex}")
    if result.input_image_data.author is not None:
        container.caption(body = f":green[Created by: {result.input_image_data.author}]")

    copy_widget_id = uuid.uuid4().int
    delete_widget_id = uuid.uuid4().int
    train_widget_id = uuid.uuid4().int

    column1, column2, column3 = container.columns(3, gap = "large")
    with column1:
        column1.button(":clipboard: Copy", on_click = on_equation_copy, args=(result.latex,),
                        key = copy_widget_id)
    with column2:
        column2.button("❌ Delete", on_click = on_delete_click, key = delete_widget_id,
                        args=(result, (copy_widget_id, delete_widget_id, train_widget_id, container.id)))
    with column3:
        disable_retrain_button: bool = True
        if 'retrain_select' in st.session_state and 'train_label' in st.session_state:
            current_equation: str = st.session_state.retrain_select
            if result.input_image_data.equation_name == current_equation and st.session_state.train_label:
                disable_retrain_button = False
        column3.button("🏋️‍♂️ Retrain", on_click = on_train_click, args = (result.uid,),
                       key = train_widget_id, disabled = disable_retrain_button)


def update_session_section_data(config_filename: str = default_config_filename):
    """
    The current prototype only supports one level of Section Headings.

    TODO - add support for nested headings
    """
    with open(config_filename, 'r') as config_file:
        st.session_state['section_config_data'] = yaml.safe_load(config_file)
        st.session_state['config_file_timestamp'] = get_config_file_timestamp()

if 'section_config_data' not in st.session_state:
    update_session_section_data()
# check if the contents of the files have changed recently
if get_config_file_timestamp() > st.session_state.config_file_timestamp:
    update_session_section_data()

def page_generator(level_one_section_name: str):
    equation_train_options = \
        [str(eq_key) for eq_key in st.session_state.section_config_data[level_one_section_name]]
    container = st.sidebar.container(border = True)
    container.subheader(body = "OCR ML Model Retrain Options", divider = "red")
    container.selectbox(label = "Retrain Equation Selection", options = equation_train_options, label_visibility = 'hidden',
                placeholder = "Select Equation to Retrain",
                help = "The Selected Equation will be processed for ML training if it is incorrect.",
                key = "retrain_select")
    container.text_input(label = "True Latex Label",
                    key = "train_label",
                    placeholder = "Training Label")

    section_data = st.session_state.section_config_data[level_one_section_name]
    equation_name: str
    equation_data: Dict
    for equation_name, equation_data_dict in section_data.items():
        try:
            equation_data = Munch(equation_data_dict)
            # not putting this on the wire, but rather, abusing the api of the class to pass data around.
            equation_entry = OCR_Result(
                uid = UintPacked(first_bits = equation_data.db_id["first_bits"],
                                 last_bits = equation_data.db_id["last_bits"]),
                input_image_data = ProtoImage(
                    equationType=ProtoImage.EquationType.UNKNOWN,
                    equation_name = equation_name,
                    author = equation_data.author,
                    parent_section = level_one_section_name
                ),
                latex = equation_data.latex
            )
            add_equation_result(equation_entry)

        except Exception as ex:
            logger.error((f"Could not generate page for Equation: {equation_name} "
                          f"in Section: {level_one_section_name}\n"
                         f"ERROR MESSAGE: {ex}"))

pages = list(st.session_state.section_config_data.keys())
selected_page: str = st.sidebar.selectbox("Equation Section", options = pages)
page_generator(selected_page)
