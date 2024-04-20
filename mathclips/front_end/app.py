import base64
from pathlib import Path

import streamlit as st
from st_pages import Page, show_pages
from streamlit_extras.app_logo import add_logo
import pandas as pd

root_dir = Path(__file__).parent.resolve()
show_pages([
    Page(path = "app.py", name = "Home", icon = "🏠"),
    Page(path = "pages/upload_page.py", name = "Image Upload Tools", icon = "🔨"),
    Page(path = "pages/notebook_page.py", name = "Math Equation Notebook", icon = "➗")])

def add_homepage_logo():
    def get_site_logo_data():
        logo_path = root_dir / "static" / "mathclips_logo.png"
        with open(logo_path, 'rb') as file:
            data = file.read()
        return base64.b64encode(data).decode()

    background_position=r"50% 0%"
    margin_top="5%"
    margin_bottom="10%"
    image_width="20%"
    image_height="50%"
    binary_string = get_site_logo_data()

    st.markdown("""
            <style>
                [data-testid="stSidebarNav"] {
                    background-image: url("data:image/png;base64,%s");
                    background-repeat: no-repeat;
                    background-position: %s;
                    margin-top: %s;
                    margin-bottom: %s;
                    background-size: %s %s;
                }
            </style>
            """ % (
        binary_string,
        background_position,
        margin_top,
        margin_bottom,
        image_width,
        image_height), unsafe_allow_html = True
    )

@st.cache_data
def create_technology_table() -> pd.DataFrame:
    st.header("Technologies Used")
    technology_table = pd.DataFrame.from_dict(
        data = dict(
            RPC = "Protobuf",
            Databases = "Mongo DB",
            Languages = "Python",
            Frontend = "Stream lit",
            Hosting = "Docker/Docker-Compose",
            Equations = "Latex",
            Queueing = "Rabbit MQ"
        ),
        orient = "index",
        dtype = str,
    )
    technology_table.index.name = "Tech Stack Component"
    technology_table.columns = ("Library",)
    return technology_table

st.set_page_config(page_title = "HOME", page_icon = "static/mathclips_logo.png")
#add_homepage_logo()
add_logo("static/mathclips_logo_small.png", height = 100)
st.header("Welcome to Mathclips")
st.markdown(f"""
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
            """)

st.header("Software Architecture")
architecture_image_path = Path(__file__).parent.resolve()/"static"/"architecture_diagram.svg"
assert architecture_image_path.exists()
st.image(str(architecture_image_path))

st.table(data = create_technology_table())