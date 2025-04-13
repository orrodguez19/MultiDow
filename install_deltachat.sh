#!/bin/bash
# Descarga el binario de deltachat CLI a un directorio escribible
wget https://github.com/deltachat/deltachat-core-rust/releases/latest/download/deltachat-cli-linux-x86_64 -O ./deltachat
# Dale permisos de ejecución
chmod +x ./deltachat