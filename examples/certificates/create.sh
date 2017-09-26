#!/bin/bash
set -e


common_name=aiowstunnel
san="DNS:localhost, \
     IP:127.0.0.1"

rm -rf *.{crt,key,csr}

# generate certificate authority private key
openssl genrsa -out rootca.key 2048

# self signed CA certificate
openssl req -x509 -new -nodes -subj "/commonName=$common_name-ca" \
        -key rootca.key -sha256 -days 1024 -out rootca.crt

# generate private key for the server (nginx)
openssl genrsa -out localhost.key 2048
# certificate request
openssl req -new -sha256 -subj "/commonName=$common_name" \
        -key localhost.key -reqexts SAN -out localhost.csr \
        -config <(cat /etc/ssl/openssl.cnf \
                  <(printf "[SAN]\nsubjectAltName=%s" "$san"))
# sign the certificate with CA
openssl x509 -req -in localhost.csr -CA rootca.crt -CAkey rootca.key \
        -out localhost.crt -days 500 -sha256 -extensions SAN \
        -CAcreateserial -CAserial rootca.srl \
        -extfile <(cat /etc/ssl/openssl.cnf \
                   <(printf "[SAN]\nsubjectAltName=%s" "$san"))

# generate private key for the client
openssl genrsa -out client.key 2048
# certificate request
openssl req -new -sha256 -subj "/commonName=$common_name-cli" \
       -key client.key -out client.csr
# sign the certificate with CA
openssl x509 -req -in client.csr -CA rootca.crt -CAkey rootca.key \
       -out client.crt -days 500 -sha256 \
       -CAcreateserial -CAserial rootca.srl

# client cert for the browser
openssl pkcs12 -export -clcerts -in client.crt -inkey client.key \
        -passout pass:admin -out client.pfx
