
all: iterable_iterator.png game_machine.png

%.png: %.dot
	dot "$<" -Tpng -o"$@"
