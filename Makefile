install:
	poetry install
project:
	poetry run project
lint:
	poetry run ruff check .
build:
	poetry build
publish:
	poetry publish --build
package-install:
	pip install dist/*.whl