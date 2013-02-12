
all: iterable_iterator.png game_machine.png telnet_filter.png everything.png \
    iterable_iterator_generator.png

%.png: %.dot
	dot "$<" -Tpng -o"$@"

run.py: Iterables,\ Iterators,\ Generators.ipynb
	python extract.py > run.py

run: run.py
	python run.py

part1.rst: Iterables,\ Iterators,\ Generators.ipynb rst.py
	python rst.py "$<" "$@"
