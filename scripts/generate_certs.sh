#!/bin/bash

generate_cert() {
    openssl req -x509 -newkey rsa:2048 \
    -keyout "certs/$1.key" -out "certs/$1.crt" \
    -days "$2" -nodes -config openssl.cnf
}

if [ ! -d "certs" ]; then
    mkdir certs
fi

generate_cert client 365
generate_cert server 365
