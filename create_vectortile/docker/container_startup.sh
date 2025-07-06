#!/bin/bash
echo "Starting container_startup.sh"
cd /tippecanoe
make
make install
echo "Finished container_startup.sh"
exec /bin/bash
