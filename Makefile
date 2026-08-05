.PHONY: all check

all:
	python3 src/generate.py
	python3 src/books.py

check:
	python3 src/books.py
