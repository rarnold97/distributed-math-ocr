def get_notebook_config_path():
    from pathlib import Path
    root_dir = Path(__file__).parent.resolve()
    return root_dir / "pages" / "default_session_equation_sections.yml"

notebook_config_path =  get_notebook_config_path()
assert notebook_config_path.exists()