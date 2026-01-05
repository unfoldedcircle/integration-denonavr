python -m pylint intg-denonavr && \
python -m flake8 intg-denonavr && \
python -m isort intg-denonavr/. && \
python -m black intg-denonavr --line-length 120