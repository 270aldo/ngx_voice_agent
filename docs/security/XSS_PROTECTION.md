# XSS Protection Implementation

## Overview

This document describes the Cross-Site Scripting (XSS) protection implementation for the NGX Voice Sales Agent. The system provides multiple layers of defense against XSS attacks through input sanitization, output encoding, and security headers.

## Architecture

### 1. Input Sanitization Layer

The `InputSanitizer` class in `src/utils/sanitization.py` provides comprehensive input sanitization:

```python
from src.utils.sanitization import InputSanitizer

sanitizer = InputSanitizer()

# Sanitize plain text
clean_text = sanitizer.sanitize_text("<script>alert('xss')</script>")
# Result: "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

# Sanitize HTML (allowing safe tags)
clean_html = sanitizer.sanitize_html(html_content, allowed_tags=['p', 'strong'])

# Sanitize filenames
safe_filename = sanitizer.sanitize_filename("../../../etc/passwd")
# Result: "___etc_passwd"

# Detect SQL injection
if sanitizer.detect_sql_injection(user_input):
    # Block the request
```

### 2. XSS Protection Middleware

The `XSSProtectionMiddleware` in `src/api/middleware/xss_protection.py` automatically sanitizes all incoming requests:

- Query parameters
- Request headers
- JSON body content
- Form data

Example configuration:
```python
from src.api.middleware.xss_protection import create_xss_protection_middleware

app.add_middleware(create_xss_protection_middleware(app))
```

### 3. Content Security Policy (CSP)

The `ContentSecurityPolicyMiddleware` sets restrictive CSP headers:

```python
from src.api.middleware.xss_protection import create_csp_middleware

# Production configuration
app.add_middleware(create_csp_middleware(app, production=True))
```

Production CSP policy:
```
default-src 'none';
script-src 'self';
style-src 'self';
img-src 'self' data: https:;
font-src 'self';
connect-src 'self';
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
upgrade-insecure-requests;
```

### 4. Model-Level Validation

Pydantic models automatically validate and sanitize inputs:

```python
from src.models.conversation import Message, CustomerData

# Message content is automatically sanitized
message = Message(content="<script>alert('xss')</script>")
# content is sanitized before storage

# Customer data is validated and sanitized
customer = CustomerData(
    name="<b>John Doe</b>",  # HTML stripped
    email="test@example.com",  # Validated
    age=25
)
```

## Security Headers

The middleware adds the following security headers to all responses:

- `X-XSS-Protection: 1; mode=block` - Enable browser XSS filter
- `X-Content-Type-Options: nosniff` - Prevent MIME sniffing
- `X-Frame-Options: DENY` - Prevent clickjacking
- `Referrer-Policy: strict-origin-when-cross-origin` - Control referrer info
- `Content-Security-Policy` - Restrict resource loading

## Input Validation Rules

### Text Fields
- HTML entities are escaped
- Null bytes removed
- Non-printable characters filtered (except newlines/tabs)
- Maximum length enforced

### Email Addresses
- RFC-compliant validation
- Normalized to lowercase
- Special characters escaped

### Phone Numbers
- Only digits and formatting characters allowed
- Length validation (7-20 characters)
- International format support

### URLs
- Only HTTP(S) and relative URLs allowed
- JavaScript/VBScript protocols blocked
- Data URIs blocked

### Filenames
- Path traversal patterns removed
- Special characters replaced with underscores
- Hidden files (starting with .) renamed
- Maximum length enforced

## SQL Injection Detection

The system detects potential SQL injection attempts:

```python
# Patterns detected:
- SQL keywords in suspicious context (UNION SELECT, DROP TABLE, etc.)
- Comment sequences (--, #, /* */)
- Quote escaping attempts (';, '=)
- Common injection payloads (1=1, OR 1=1, admin'--)
```

## Usage Examples

### 1. Manual Sanitization

```python
from src.utils.sanitization import sanitize_request_data

# Sanitize entire request data
clean_data = sanitize_request_data({
    "name": "<script>alert('xss')</script>",
    "bio": "<p>Hello <strong>world</strong></p>",
    "tags": ["<b>tag1</b>", "tag2"]
})
```

### 2. Markdown Rendering

```python
from src.utils.sanitization import create_safe_markdown

# Safely render markdown with XSS protection
safe_html = create_safe_markdown("This is **bold** text")
```

### 3. Field-Specific Validation

```python
from src.utils.input_validators import CustomerDataValidator

# Validate customer inputs
clean_name = CustomerDataValidator.validate_customer_name(name)
clean_email = CustomerDataValidator.validate_customer_email(email)
clean_phone = CustomerDataValidator.validate_customer_phone(phone)
```

## Testing

Run XSS protection tests:
```bash
pytest tests/unit/utils/test_sanitization.py -v
pytest tests/unit/middleware/test_xss_protection.py -v
```

## Monitoring

The middleware logs all XSS protection violations:

```python
2024-01-19 10:23:45 WARNING XSS protection triggered for POST /api/conversation
{
    "violations": ["Query param: evil=<script>alert(1)</script>"],
    "client_ip": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
}
```

## Best Practices

1. **Always sanitize user inputs** - Never trust any user-provided data
2. **Use the middleware** - Let it handle sanitization automatically
3. **Validate at the model level** - Add validators to Pydantic models
4. **Escape output** - Always escape when rendering user content
5. **Set security headers** - Use restrictive CSP policies in production
6. **Monitor violations** - Review logs for attack attempts
7. **Keep dependencies updated** - Regular updates for bleach and other security libraries

## Configuration

Environment variables for XSS protection:

```env
# Enable/disable XSS protection middleware
XSS_PROTECTION_ENABLED=true

# Log XSS violations
XSS_LOG_VIOLATIONS=true

# Custom CSP policy (JSON format)
CSP_POLICY='{"default-src": ["self"], "script-src": ["self"]}'

# Maximum input lengths
MAX_TEXT_LENGTH=10000
MAX_HTML_LENGTH=50000
MAX_FILENAME_LENGTH=255
```

## Troubleshooting

### Issue: Legitimate HTML content is being stripped

**Solution**: Configure allowed tags for HTML fields:
```python
sanitizer.sanitize_html(content, allowed_tags=['p', 'br', 'strong', 'em'])
```

### Issue: False positive SQL injection detection

**Solution**: Use parameterized queries and disable SQL detection for specific fields:
```python
# Disable SQL detection for a specific field
if field_name not in ['search_query', 'filter']:
    if sanitizer.detect_sql_injection(value):
        # Block request
```

### Issue: Performance impact from sanitization

**Solution**: 
1. Cache sanitized values when possible
2. Use async processing for large payloads
3. Configure field-specific rules to skip unnecessary checks

## Security Considerations

1. **Defense in Depth**: XSS protection is one layer - also use:
   - Output encoding
   - HTTPOnly cookies
   - Secure session management
   - Regular security audits

2. **Regular Updates**: Keep security libraries updated:
   ```bash
   pip install --upgrade bleach
   pip install --upgrade markupsafe
   ```

3. **Penetration Testing**: Regularly test with tools like:
   - OWASP ZAP
   - Burp Suite
   - Custom XSS payloads

4. **Content Type Validation**: Always validate Content-Type headers:
   - Reject unexpected content types
   - Enforce JSON for API endpoints
   - Validate file uploads separately