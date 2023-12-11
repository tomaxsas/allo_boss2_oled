clean:
	rm -rf build

build-dir:
	mkdir build

prepare: build-dir
	cp -r debian setup.py allo_boss2 allo_boss2_remote.toml build

install-deps:
	apt-get install -y debhelper-compat dh-python python3-all python3-setuptools systemd

build: install-deps prepare
	cd build && dpkg-buildpackage --build=binary
