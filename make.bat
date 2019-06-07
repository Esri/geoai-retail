:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: VARIABLES                                                                    :
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

SETLOCAL
SET PROJECT_DIR=%cd%
SET PROJECT_NAME="geoai-retail"
SET ENV_NAME=geoai-retail
SET CONDA_PARENT=arcgispro-py3

:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
:: COMMANDS                                                                     :
:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

:: Make Dataset
GOTO %1

:data
	activate %ENV_NAME%
	python src/data/make_dataset.py
	ECHO ">>> Data processed."
	EXIT
	
:: Create the local environment by cloning the parent environment
:env_create
	conda create --yes --name %ENV_NAME% --clone %CONDA_PARENT%
	ECHO ">>> New conda environment, %ENV_NAME%, created. Activate with:"
	ECHO.
	ECHO "- activate %ENV_NAME%"
	ECHO.
	ECHO "- make env_activate"
	EXIT
	
:: Export the current environment
:env_export
	conda env export --name %ENV_NAME% > environment.yml
	ECHO ">>> %PROJECT_NAME% conda environment exported to ./environment.yml"
	EXIT 
	
:: Build the local environment from the environment file
:env_build
	conda env create --yes -f environment.yml
	EXIT

:create_kernel 
	python -m ipykernel install --user --name %ENV_NAME% --display-name "%PROJECT_NAME%"

:: Run all tests in module
:test
	activate %PROJECT_NAME%
	pytest
	EXIT
	
EXIT
