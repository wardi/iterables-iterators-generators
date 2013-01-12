
all: iterable_iterator.png game_machine.png telnet_filter.png

%.png: %.dot
	dot "$<" -Tpng -o"$@"
