#!/bin/bash

echo "🔐 Initial Check and Configuration..."

TORRC_FILE="/etc/tor/torrc"
HS_DIR="/var/lib/tor/hidden_service"
HS_HOSTNAME_FILE="$HS_DIR/hostname"

# Messaggi colorati
green() { echo -e "\e[32m$1\e[0m"; }
yellow() { echo -e "\e[33m$1\e[0m"; }
red() { echo -e "\e[31m$1\e[0m"; }

# 1. Controlla se Tor è installato
TOR_NEWLY_INSTALLED=false
if ! command -v tor &> /dev/null; then
    yellow "🛠️ Tor non trovato. Procedo all'installazione..."
    sudo apt update
    sudo apt install -y tor
    TOR_NEWLY_INSTALLED=true
else
    green "✅ Tor è già installato."
fi

# 2. Crea la directory HiddenService (se non esiste)
if [ ! -d "$HS_DIR" ]; then
    yellow "📁 Creo la directory hidden_service..."
    sudo mkdir -p "$HS_DIR"
fi

# 3. Assicura i permessi corretti
sudo chown -R debian-tor:debian-tor "$HS_DIR"
sudo chmod 700 "$HS_DIR"

# 4. Verifica se configurazione HiddenService è già nel torrc
if ! grep -q "^HiddenServiceDir $HS_DIR" "$TORRC_FILE"; then
    yellow "➕ Aggiungo configurazione HiddenService a $TORRC_FILE..."

    sudo tee -a "$TORRC_FILE" > /dev/null <<EOF

HiddenServiceDir $HS_DIR
HiddenServicePort 80 127.0.0.1:8080
EOF
else
    green "✅ Configurazione HiddenService già presente in torrc."
fi

# 5. Riavvia Tor
yellow "🔁 Riavvio Tor..."
sudo systemctl restart tor

# 6. Attendi la generazione dell'indirizzo onion
echo "⏳ Attendo generazione indirizzo .onion..."
sleep 3  # attesa per sicurezza

# 7. Verifica hostname
if [ -f "$HS_HOSTNAME_FILE" ]; then
    ONION=$(sudo cat "$HS_HOSTNAME_FILE" | grep -oP "[a-z0-9]{16,56}\.onion")
    if [ -n "$ONION" ]; then
        green "✅ Indirizzo onion disponibile: http://$ONION"
    else
        red "❌ Il file hostname esiste ma non contiene un indirizzo .onion valido."
        exit 1
    fi
else
    red "❌ Il file hostname non è stato creato. Controlla la configurazione Tor."
    exit 1
fi

# 8. Avvio server Flask
echo "🚀 Avvio An0nChat su 127.0.0.1:8080"
python3 anonchat.py
