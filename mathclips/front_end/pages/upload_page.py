from typing import Callable, Optional
from dataclasses import dataclass, fields
from pathlib import Path
import uuid

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile
from streamlit_drawable_canvas import st_canvas
import pymongo
from pymongo.database import Database
import gridfs
from PIL import Image

from mathclips.services.mongodb import MathSymbolImageDatabase
#from services.logger import logger as LOGGER
from mathclips.proto.pb_py_classes.image_pb2 import Image as ProtoImage
from mathclips.proto.pb_py_classes.uint_packed_bytes_pb2 import UintPackedBytes as UintPacked
from mathclips.services.rmq import publish_proto_message
from mathclips.services import IngestQueueNames

@st.cache_resource
def init_mongo_db_connection():
    return pymongo.MongoClient(**st.secrets["mongo"])

@st.cache_resource
def init_mongo_gridfs(_client: Database) -> gridfs.GridFS:
    return gridfs.GridFS(_client, collection = MathSymbolImageDatabase.collection_name)

@st.cache_resource
def init_image_database(_db: Database, _file_storage: gridfs.GridFS):
    return MathSymbolImageDatabase(_db, _file_storage)

st.set_page_config(page_title = "Image Upload Tools", page_icon = "static/mathclips_logo_small.png")

mongo_client = init_mongo_db_connection()
db = mongo_client["mathclips_data"]
grid_fs = init_mongo_gridfs(db)
image_db: MathSymbolImageDatabase = init_image_database(db, grid_fs)

@dataclass
class PageFunctionMap:
    upload_raw_image: Callable = None
    draw_equation: Callable = None

    def get_web_options(self):
        return [field.name.replace("_", " ") for field in fields(self)]

    def get_callback(self, web_option: str) -> Callable:
        return getattr(self, web_option.replace(" ", "_"), None)

def author_name_widget() -> str | None:
    # input text box
    st.text_input("Author/Contributor Name", key="author_name")
    return st.session_state.author_name

def equation_title_widget() -> str | None:
    st.text_input("Equation Title", key = "equation_title")
    return st.session_state.equation_title

def section_name_widget() -> str | None:
    st.text_input("Equation Section", key = "equation_section")
    return st.session_state.equation_section

def draw_widget():

    input_author_name: str = author_name_widget()
    input_equation_title: Optional[str] = equation_title_widget()
    input_equation_section: Optional[str] = section_name_widget()

    st.sidebar.header("Draw Configuration")

    st.markdown(
        """
Draw Equation on the canvas.
Resulting image in "Output Image View" will deploy to ML pipeline!
* Configure canvas in the sidebar
        """)

    # Specify canvas parameters in application
    stroke_width = st.sidebar.slider("Stroke width: ", 1, 25, 3)
    stroke_color = st.sidebar.color_picker("Stroke color hex: ")
    background_color = st.sidebar.color_picker("Background color hex: ", "#eee")
    realtime_update = st.sidebar.checkbox("Update in realtime", True)

    # Create a canvas component
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",  # Fixed fill color with some opacity
        stroke_width=stroke_width,
        stroke_color=stroke_color,
        background_color=background_color,
        background_image= None,
        update_streamlit=realtime_update,
        height=200,
        width = 800,
        point_display_radius=0,
        display_toolbar=st.sidebar.checkbox("Display toolbar", True),
        key="draw_box",)

    def on_upload_click():
        if canvas_result.image_data is not None:
            if input_author_name and input_equation_title and input_equation_section:
                image = Image.fromarray(canvas_result.image_data)
                image_name = f"draw_widget_image_{uuid.uuid4().int}.png"
                file_id: UintPacked = image_db.store_image(
                     image = image,
                     image_basename = image_name,
                     equation_type = ProtoImage.EquationType.HANDWRITTEN,
                     equation_name = input_equation_title,
                     author_name = input_author_name,
                     equation_section = input_equation_section)
                assert file_id is not None
                print("UPLOADED FILE ID: ", file_id)
                # now we must create the appropriate IPC message to kick of pipelines
                image_message = ProtoImage(uid = file_id, equationType = ProtoImage.EquationType.HANDWRITTEN,
                                        equation_name = input_equation_title,
                                        author = input_author_name,
                                        parent_section = input_equation_section)
                publish_proto_message(image_message, IngestQueueNames.ML_PIPELINE_QUEUE)
                st.toast("Sent Image to Machine Learning Pipeline, check Notebook section for results!",
                        icon = "🤖")

    disable_button = not input_author_name or not input_equation_section or not input_equation_title
    st.button("upload image", key = "draw_upload", disabled = disable_button,
              on_click = on_upload_click)

def image_uploader():

    input_author_name: Optional[str] = author_name_widget()
    input_equation_title: Optional[str] = equation_title_widget()
    input_equation_section: Optional[str] = section_name_widget()

    disable_uploader: bool = not input_author_name \
        or not input_equation_title \
        or not input_equation_section

    def on_image_file_upload():
        if 'image_file_uploader' in st.session_state:
            uploaded_file = st.session_state.image_file_uploader
            if uploaded_file:
                st.toast(f"{uploaded_file.name} Sucessfully Uploaded", icon = "✅")
                # wrapping in a Path to omit directory structure
                image_basename: str = Path(uploaded_file.name).name
                pil_image = Image.open(uploaded_file)
                image_fid: UintPacked = image_db.store_image(image = pil_image, image_basename = image_basename,
                                                            equation_type = ProtoImage.EquationType.DIGITAL,
                                                            equation_name = input_equation_title, author_name = input_author_name,
                                                            equation_section = input_equation_section)

                # know we must create the appropriate IPC message to kick of pipelines
                image_message = ProtoImage(uid = image_fid, equationType = ProtoImage.EquationType.DIGITAL,
                                        equation_name = input_equation_title,
                                        author = input_author_name,
                                        parent_section = input_equation_section)
                publish_proto_message(image_message, IngestQueueNames.ML_PIPELINE_QUEUE)
                st.toast("Sent Image to Machine Learning Pipeline, check Notebook section for results!",
                        icon = "🤖")
    # this will be disabled until all above metadata is populated
    uploaded_file: UploadedFile = st.file_uploader(label = "Upload Equation Image",
                            type = ['png', 'jpg'], key = "image_file_uploader",
                            on_change = on_image_file_upload,
                            disabled = disable_uploader, )

page_map = PageFunctionMap(
    upload_raw_image = image_uploader,
    draw_equation = draw_widget)

page_name: str = st.sidebar.selectbox("Page:", options = page_map.get_web_options())
page_function = page_map.get_callback(page_name)
if page_function:
    page_function()
