---
title: Security Policy
---

# Security Policy

## Signatures

The Ruqqus master cryptographic key was generated with the `secrets` module and is appropriate for cryptographically secure functions.

If you need to sign something, use the following functions:

    from ruqqus.helpers.security import *
    
    hashstr = generate_hash(string)

    hashstr_is_valid = validate_hash(string, hashstr)

This will generate (or validate) an HMAC hex digest of the string using the Ruqqus master key.

## Account validation

Do not write your own account validation methods within route functions. Instead, use `from ruqqus.helpers.wrappers import *` and use the following decorators:

* Any function that requires a logged-in account must be decorated with `@auth_required`. If the user additionally must not be banned, use `@is_not_banned` instead.

* Any function that requires a logged-in administrator account must be decorated with `@admin_level_required(x)`, where `x` is the administrator level needed to execute the function.

* Any other function that does not strictly need a logged in session, but would benefit from having one, should use `@auth_desired`.

In all cases, the logged in user object is passed to the route function as the variable `v`.

## Sanitization

To sanitize user-generated HTML for safe display:

    from ruqqus.helpers.sanitize import sanitize

    html=sanitize(html, linkgen=False)

If linkgen is true, valid URLs will be converted into `<a>` elements.


## CSRF

The following procedures are in place to prevent cross-site request forgery (CSRF).

1. All forms for user input must include the following element, copied exactly:

    `<input type="hidden" name="formkey", value="{{ v.formkey }}">`
    
2. Functions handling incoming POST requests **must** be decorated with `@validate_formkey`. Above that decorator should be one of `@auth_required`, `@admin_level_required(x)`, or `@is_not_banned`.

