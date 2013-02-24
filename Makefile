
all: iterable_iterator.png game_machine.png telnet_filter.png everything.png \
    iterable_iterator_generator.png

%.png: %.dot
	dot "$<" -Tpng -o"$@"

rps_server.py: Iterables,\ Iterators,\ Generators.ipynb
	python extract.py > $@

run: rps_server.py
	python $<

part1.rst: Iterables,\ Iterators,\ Generators.ipynb rst.py
	python rst.py "$<" "$@"
