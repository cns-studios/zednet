# 🌐 ZedNet - Decentralized Web Platform

<div align="center">

**Privacy Focused | Censorship-Resistant | Peer-to-Peer**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Security: Mandatory](https://img.shields.io/badge/security-mandatory-red.svg)](docs/SECURITY.md)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange.svg)](https://github.com/cns-studios/zednet/releases)

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Security](#-security) • [Legal](#%EF%B8%8F-legal-notice) • [Contributing](#-contributing)

</div>

---

## ⚠️ CRITICAL LEGAL & SECURITY NOTICE

**READ THIS BEFORE USING ZEDNET:**

- **Alpha Software**: This is experimental software. Use at your own risk.
- **Legal Responsibility**: You are solely responsible for content you create, distribute, or access.
- **Anonymity Not Guaranteed**: VPN/Tor usage is recommended but not enforced by the protocol.
- **No Content Moderation**: This is a decentralized system. Report illegal content.
- **Jurisdiction Matters**: Check local laws. ZedNet may be illegal in some jurisdictions.

**By using ZedNet, you accept full responsibility for your actions.**

---

## What is ZedNet?

ZedNet is a **privacy-focused, decentralized web platform** that enables:

- **Anonymous Publishing**: Host websites without revealing your identity
- **Censorship Resistance**: Content distributed via BitTorrent DHT
- **Mutable Content**: Update your site while keeping the same ID (BEP 46)
- **End-to-End Encryption**: All P2P traffic is encrypted
- **Security First**: Built with security as the primary concern

### How It Works

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Creator   │         │  BitTorrent  │         │   Visitor   │
│             │───────▶│     DHT       │◀───────│             │
│ Publishes   │         │              │         │  Downloads  │
│ via BEP 46  │         │ Distributed  │         │  & Seeds    │
└─────────────┘         └──────────────┘         └─────────────┘
       │                                                  │
       │                                                  │
       └──────────────── Encrypted P2P ─────────────────┘
                    (Mutable Torrent Updates)
```

1. **Create**: Generate a cryptographic keypair (Ed25519)
2. **Publish**: Upload your website as a mutable torrent (BEP 46)
3. **Share**: Distribute your public key (ZedNet ID)
4. **Access**: Visitors download and seed your content locally
5. **Update**: Sign new versions with your private key

---

## Features

### Core Features
- **Ed25519 Cryptographic Identity**: Immutable site IDs based on public keys
- **BEP 46 Mutable Torrents**: Update content without changing the site ID
- **Mandatory Encryption**: All P2P traffic encrypted (RC4/AES)
- **Local Web Server**: Serve content via `http://127.0.0.1:9999`
- **Cross-Platform**: Windows, macOS, Linux support

### Security Features
- **VPN Kill Switch**: Auto-shutdown on VPN disconnection   
- **Path Traversal Protection**: Military-grade file access sanitization
- **Audit Logging**: Immutable logs of all security events
- **Content Scanning**: Hash-based malware detection
- **Rate Limiting**: DDoS protection on local server
- **Secure Key Storage**: Encrypted private key storage

### Privacy Features
- **Anonymous**: No client fingerprinting
- **VPN Detection**: Warns if VPN appears inactive
- **Local-Only Server**: Never exposed to external network
- **No Telemetry**: Zero data collection

---

## Public Site Index (Optional)

While ZedNet is fully decentralized for content sharing, a centralized public index is necessary for site discovery and moderation. This is due to limitations in the underlying `aiotorrent` library (specifically, the lack of support for mutable torrents, BEP46) which prevent a fully decentralized discovery mechanism.

The provided serverless functions allow anyone to host their own public index for a community. This is a compromise that allows for:
- **Moderation:** A central point to curate a list of public sites.
- **Discoverability:** A simple way for users to find new content.
- **Contributions Welcome:** We encourage the community to help improve the DHT-based discovery features to remove the need for this centralized index.

### Use official Pubic Site Index (Recommended)
**The official Site Index moderates malicious sites and has the largest know site pool**. If you whish to add your Own Index or a Site to the public Index, open a Github Issue and upload your `sites.json` file. Our team will check it and merge the contents to the official index.


**1. Set up .env file**
- Create a `.env` file in your zednet directory and copy these URLs:
    ```
    SITES_JSON_URL="https://69209cbcd7387f152410e363--zednet-backend.netlify.app/.netlify/functions/get_sites"
    SUBMIT_SITE_URL="https://69209cbcd7387f152410e363--zednet-backend.netlify.app/.netlify/functions/submit_site"
   ```
- Thats it! Youre all set and can skip the other parts of this section.



### Hosting Your Own Index

You can host your own public index for free using Netlify and Upstash.

**1. Set up Upstash Redis:**
- Create a free account at [Upstash](https://upstash.com/).
- Create a new Redis database.
- Copy the `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` from your database details page.

**2. Deploy to Netlify:**
- Fork this repository to your GitHub account.
- Create a new site on Netlify and connect it to your forked repository.
- In your Netlify site's "Site configuration" -> "Environment variables", add the following two variables:
  - `UPSTASH_REDIS_REST_URL`: The value you copied from Upstash.
  - `UPSTASH_REDIS_REST_TOKEN`: The value you copied from Upstash.
- Netlify will automatically detect the `netlify.toml` file and deploy the serverless functions from the `netlify/functions` directory.

**3. Configure Your Local ZedNet App:**
- In the root of your local ZedNet project, create a file named `.env`.
- Edit the `.env` file and replace the placeholder URLs with your actual Netlify function URLs:
  ```
  SITES_JSON_URL="https://your-netlify-site-name.netlify.app/.netlify/functions/get_sites"
  SUBMIT_SITE_URL="https://your-netlify-site-name.netlify.app/.netlify/functions/submit_site"
  ```
- Start the ZedNet application. It will now use your public index for site discovery and submission.

---

## Installation

### Prerequisites

- **Python 3.9+** ([Download](https://www.python.org/downloads/))
- **libtorrent 2.0+** (installed automatically)
- **VPN or Tor** (strongly recommended)

### Quick Start (Linux/macOS)

```bash
# Clone the repository
git clone https://github.com/cns.studios/zednet.git
cd zednet

# Run setup script
chmod +x setup.sh
./setup.sh

# Activate virtual environment
source venv/bin/activate

# Start ZedNet
python main.py
```

### Quick Start (Windows)

```batch
# Clone the repository
git clone https://github.com/cns-studios/zednet.git
cd zednet

# Run setup script
setup.bat

# Activate virtual environment
venv\Scripts\activate.bat

# Start ZedNet
python main.py
```

### Manual Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start application
python main.py
```

---

## Usage

### First Run

1. **Accept Terms**: You must accept the Terms of Service
2. **VPN Check**: Ensure VPN/Tor is active
3. **Dashboard**: Access `http://127.0.0.1:9999` in your browser

### Creating a Site

```bash
# Using the GUI (Automaticly open)
python gui/interface.py

# Using CLI (In beta)
python -m tools.create_site ./my-website
```

This generates:
- **Private Key**: `data/keys/<site_id>.key` (KEEP SECRET!)
- **Public Key**: Your ZedNet Site ID (share this)

### Publishing Content

**Button in the GUI**

```python
from core.publisher import SitePublisher

publisher = SitePublisher()
site_id = publisher.publish_site(
    content_dir="./my-website",
    private_key_file="data/keys/mysite.key"
)

print(f"Site published: {site_id}")
```

### Accessing a Site

1. **Add Site**: Enter the ZedNet Site ID in the GUI
2. **Download**: Content downloads automatically via P2P
3. **Browse**: Open `http://127.0.0.1:9999/site/<SITE_ID>/index.html` or use `http://127.0.0.1:9999/sites` to see all publicly listed ones

### Updating Your Site

```python
# Make changes to your website files
# Then re-publish with the same private key

publisher.update_site(
    content_dir="./my-website-v2",
    private_key_file="data/keys/mysite.key"
)

# Visitors automatically get the update!
```

---

## Security

### Security Model

ZedNet uses **defense-in-depth** security:

```
┌─────────────────────────────────────────┐
│  User Responsibility (VPN/Tor)          │
├─────────────────────────────────────────┤
│  Application Layer                      │
│  ├─ Input Validation                    │
│  ├─ Path Sanitization                   │
│  ├─ Rate Limiting                       │
│  └─ Audit Logging                       │
├─────────────────────────────────────────┤
│  P2P Layer                              │
│  ├─ Mandatory Encryption                │
│  ├─ Signature Verification              │
│  └─ DHT Security                        │
├─────────────────────────────────────────┤
│  Network Layer                          │
│  ├─ VPN/Tor (user-provided)             │
│  ├─ Kill Switch (app-enforced)          │
│  └─ Local-Only Server (127.0.0.1)       │
└─────────────────────────────────────────┘
```

### Reporting Security Issues

**Please** open public issues for security vulnerabilities.


See [SECURITY.md](SECURITY.md) for our responsible disclosure policy.

---

## Legal Notice

### Terms of Service

By using ZedNet, you agree to:

- Comply with all local laws and regulations
- Not distribute illegal content (CSAM, malware, etc.)
- Take responsibility for your anonymity (use VPN/Tor)
- Report illegal content via the built-in reporting system

Full terms: [TERMS_OF_SERVICE.md](legal/TERMS_OF_SERVICE.md)

### Privacy Policy

ZedNet does NOT collect:
- Personal information
- Browsing history
- Telemetry data

ZedNet DOES store locally:
- Audit logs (on your device only)
- Downloaded content (on your device only)
- Your private keys (encrypted, on your device only)

Full policy: [PRIVACY_POLICY.md](legal/PRIVACY_POLICY.md)

### Disclaimer

```
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
THE AUTHORS ARE NOT LIABLE FOR ANY MISUSE OR ILLEGAL ACTIVITY.
```

---

## Architecture

```
zednet/
├── core/                   # Core security & P2P logic
│   ├── security.py         # Cryptography & sanitization
│   ├── p2p_engine.py       # libtorrent wrapper
│   ├── publisher.py        # Site publishing (BEP 46)
│   ├── downloader.py       # Site downloading & seeding
│   ├── vpn_check.py        # VPN detection
│   ├── killswitch.py       # Emergency shutdown
│   ├── audit_log.py        # Security event logging
│   ├── content_scanner.py  # Malware detection
│   └── storage.py          # Secure file operations
│
├── server/                 # Local web server
│   └── local_server.py     # Flask server (127.0.0.1:9999)
│
├── gui/                    # User interface
│   ├── interface.py        # Main GUI (PyQt5)
│   ├── dashboard.py        # Dashboard view
│   └── settings.py         # Settings panel
│
├── tools/                  # CLI utilities
│   ├── create_site.py      # Site creation tool
│   ├── import_site.py      # Import existing site
│   └── export_keys.py      # Key management
│
├── tests/                  # Test suite
│   ├── test_security.py    # Security tests (CRITICAL)
│   ├── test_p2p.py         # P2P functionality tests
│   └── test_server.py      # Server tests
│
├── legal/                  # Legal documents
│   ├── TERMS_OF_SERVICE.md
│   └── PRIVACY_POLICY.md
│
├── docs/                   # Documentation
│   ├── SECURITY.md         # Security documentation
│   ├── DEVELOPMENT.md      # Developer guide
│   └── API.md              # API reference
│
├── config.py               # Configuration
├── main.py                 # Entry point
└── requirements.txt        # Dependencies
```

---

## Development

### Running Tests

```bash
# All tests
pytest tests/ -v

# Security tests only (must pass 100%)
pytest tests/test_security.py -v

# With coverage
pytest tests/ --cov=core --cov=server --cov-report=html
```

### Code Quality

```bash
# Format code
black core/ server/ gui/ tools/

# Lint
flake8 core/ server/ gui/ tools/

# Type check
mypy core/ server/ gui/ tools/
```

### Building Executables

```bash
# Windows
pyinstaller --onefile --windowed --name ZedNet main.py

# macOS
pyinstaller --onefile --windowed --name ZedNet --icon=icon.icns main.py

# Linux
pyinstaller --onefile --name zednet main.py
```

---

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

### Priority Areas

- **Security auditing** (highest priority)
- **BEP 46 implementation** (partially complete - not fully possible with the current `aiotorrent` libary)
- **GUI improvements** (PyQt5)
- **Documentation**
- **Cross-platform testing**

### Development Setup

```bash
# Fork and clone
git clone https://github.com/cns-studios/zednet.git
cd zednet

# Create feature branch
git checkout -b feature/your-feature

# Install dev dependencies
pip install -r requirements-dev.txt

# Make changes and test
pytest tests/ -v

# Submit pull request
```

---

## Project Status

### Completed
- [x] Core security framework
- [x] Path traversal protection
- [x] Audit logging
- [x] VPN kill switch
- [x] Content scanning framework
- [x] Local web server
- [x] Terms of Service / Privacy Policy

### In Progress
- [ ] BEP 46 mutable torrent implementation (60%)
- [ ] GUI application (70%)
- [ ] Site publishing tools (40%)
- [ ] DHT integration (90%)

### Planned 
- [ ] Tor integration
- [ ] Multi-language support
- [ ] Plugin system
- [ ] Mobile clients (Android/iOS)
- [ ] Browser extension

---

## Acknowledgments

- **BitTorrent Protocol**: For the DHT and mutable torrent spec (BEP 46)
- **libtorrent**: Arvid Norberg and contributors
- **The Tor Project**: For privacy research and tools
- **ZeroNet**: Inspiration for decentralized web architecture

---

## License

```
MIT License

Copyright (c) 2024 ZedNet Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Contact & Support

- **Issues**: [GitHub Issues](https://github.com/cns-studios/zednet/issues)
- **Discussions**: [GitHub Discussions](https://github.com/cns-studios/zednet/discussions)

---

<div align="center">

**⚡ Built with Privacy in Mind**

[⬆ Back to Top](#-zednet---decentralized-web-platform)

</div>