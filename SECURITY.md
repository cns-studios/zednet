# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

**DO NOT** open public GitHub issues for security vulnerabilities.

### Response Time

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity


## Security Best Practices for Users

1. **Always use a VPN or Tor**
2. **Encrypt your disk** (BitLocker, FileVault, LUKS)
3. **Use strong passwords** for key encryption
4. **Back up private keys** securely
5. **Keep software updated**
6. **Review audit logs** regularly

## Security Features

- ✅ Mandatory P2P encryption
- ✅ Path traversal protection
- ✅ VPN kill switch
- ✅ Audit logging
- ✅ Content scanning
- ✅ Rate limiting

## Known Limitations

- ⚠️ VPN detection can be bypassed
- ⚠️ No built-in Tor integration (yet)
- ⚠️ DHT traffic is visible to ISP
- ⚠️ No content moderation by default