#!/usr/bin/with-contenv bashio

bashio::log.info "Khởi động Lumentree Solar Guard Daemon Add-on..."

exec python3 /solar_ac_daemon.py
