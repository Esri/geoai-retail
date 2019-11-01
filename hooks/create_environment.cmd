call conda create --name {{cookiecutter.conda_environment_name}} --clone arcgispro-py3
call activate arcgis
call conda config --prepend channels conda-forge
call conda config --prepend channels esri
call conda install shapely cookiecutter python-dotenv nodejs scikit-learn pillow pyarrow fastparquet snappy -y
call conda update arcgis=1.6.2 pytest -y
call conda update -c defaults numpy -y
jupyter labextension install @jupyter-widgets/jupyterlab-manager -y
jupyter labextension install arcgis-map-ipywidget@1.6.2 -y