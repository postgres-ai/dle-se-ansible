#!/bin/bash

# Start systemd in the background
/lib/systemd/systemd &

# Run dockerd in the foreground
exec dockerd
