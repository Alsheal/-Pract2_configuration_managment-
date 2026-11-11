PYTHON ?= python3
CONFIG ?= config.yaml

.PHONY: install run test clean

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	PYTHONPATH=src $(PYTHON) -m dependency_visualizer.main -c $(CONFIG)

test:
	PYTHONPATH=src $(PYTHON) -m pytest -v

clean:
	rm -f *.svg *.mmd