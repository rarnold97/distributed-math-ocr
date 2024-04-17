from pathlib import Path

import streamlit as st


def on_image_file_upload(image_filename: Path):
    print(image_filename)

# input text box
st.text_input("Author/Contributor Name", key="author_name")
input_author_name: str = st.session_state.author_name

st.sidebar.file_uploader(label = ":frame_with_picture: Upload Equation Image",
                         type = ['png', 'jpg'], key = "image_file_uploader",
                         )